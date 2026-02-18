from __future__ import annotations

import queue
import threading
from datetime import datetime
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from .assets import ResolvedAssets, resolve_assets
from .audio import AudioPlayer
from .backends import BackendSelectionError, select_backend
from .config import AppConfig, load_config
from .controller import ControllerEvent, PlaybackController
from .export import save_speech_to_mp3
from .pdf_import import extract_pdf_text
from .text_processing import normalize_text


@dataclass(slots=True)
class AppRuntime:
    config: AppConfig
    assets: ResolvedAssets
    backend: object
    controller: PlaybackController
    text: str = ""
    status_message: str = "Ready"
    voice_status: str = "Voice: Missing"
    backend_status: str = "Backend: Unknown"
    _mp3_save_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _mp3_save_thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _mp3_save_results: "queue.Queue[tuple[Path | None, Exception | None]]" = field(
        default_factory=queue.Queue,
        init=False,
        repr=False,
    )
    _is_saving_mp3: bool = field(default=False, init=False, repr=False)

    @property
    def status_bar_items(self) -> list[str]:
        return [
            self.voice_status,
            self.backend_status,
            f"State: {self.status_message}",
        ]

    @property
    def status_bar_text(self) -> str:
        return " | ".join(self.status_bar_items)

    def set_text(self, value: str) -> None:
        self.text = normalize_text(value)

    def play(self) -> bool:
        if not self.text:
            self.status_message = "Enter text in the text area."
            return False

        started = self.controller.start(self.text, voice=self.config.default_voice)
        if not started:
            self.status_message = "Playback is already running."
        return started

    def stop(self) -> bool:
        return self.controller.stop()

    def save_mp3(self, output_path: Path | None = None) -> Path | None:
        if not self.text:
            self.status_message = "Enter text in the text area."
            return None

        selected_output = output_path or _default_mp3_output_path()
        try:
            saved_path = save_speech_to_mp3(
                backend=self.backend,
                text=self.text,
                voice=self.config.default_voice,
                sample_rate=self.config.sample_rate,
                output_path=selected_output,
            )
        except Exception as exc:
            self.status_message = f"Unable to save MP3: {exc}"
            return None

        self.status_message = f"Saved MP3: {saved_path}"
        return saved_path

    @property
    def is_saving_mp3(self) -> bool:
        with self._mp3_save_lock:
            return self._is_saving_mp3

    def start_mp3_save(self, output_path: Path | None = None) -> bool:
        if not self.text:
            self.status_message = "Enter text in the text area."
            return False

        selected_output = output_path or _default_mp3_output_path()

        with self._mp3_save_lock:
            if self._is_saving_mp3:
                self.status_message = "MP3 save is already in progress."
                return False

            self._clear_mp3_save_results()
            self._is_saving_mp3 = True
            self.status_message = "Saving MP3..."
            save_thread = threading.Thread(
                target=self._run_mp3_save_worker,
                kwargs={
                    "backend": self.backend,
                    "text": self.text,
                    "voice": self.config.default_voice,
                    "sample_rate": self.config.sample_rate,
                    "output_path": selected_output,
                },
                daemon=True,
                name="kookie-save-mp3",
            )
            self._mp3_save_thread = save_thread

        save_thread.start()
        return True

    def poll_mp3_save(self) -> None:
        latest_result: tuple[Path | None, Exception | None] | None = None
        while True:
            try:
                latest_result = self._mp3_save_results.get_nowait()
            except queue.Empty:
                break

        if latest_result is None:
            return

        saved_path, error = latest_result

        with self._mp3_save_lock:
            self._is_saving_mp3 = False
            self._mp3_save_thread = None

        if error is not None:
            self.status_message = f"Unable to save MP3: {error}"
            return

        if saved_path is not None:
            self.status_message = f"Saved MP3: {saved_path}"
            return

        self.status_message = "Unable to save MP3: Unknown save failure"

    def load_pdf(
        self,
        pdf_path: Path,
        *,
        loader: Callable[[Path], str] = extract_pdf_text,
    ) -> str | None:
        try:
            text = loader(pdf_path)
        except Exception as exc:
            self.status_message = f"Unable to load PDF: {exc}"
            return None

        self.set_text(text)
        self.status_message = f"Loaded PDF: {pdf_path.name}"
        return text

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        self.controller.wait_until_idle(timeout=timeout)

    @property
    def backend_name(self) -> str:
        return getattr(self.backend, "name", self.backend.__class__.__name__.lower())

    def on_controller_event(self, event: ControllerEvent) -> None:
        if event.kind == "error":
            self.status_message = f"Speech generation failed: {event.message}"
            return

        if event.state.value == "idle":
            self.status_message = "Ready"
        elif event.state.value == "playing":
            self.status_message = "Playing"
        elif event.state.value == "synthesizing":
            self.status_message = "Generating speech"
        elif event.state.value == "stopping":
            self.status_message = "Stopping"

    def _clear_mp3_save_results(self) -> None:
        while True:
            try:
                self._mp3_save_results.get_nowait()
            except queue.Empty:
                return

    def _run_mp3_save_worker(
        self,
        *,
        backend: object,
        text: str,
        voice: str,
        sample_rate: int,
        output_path: Path,
    ) -> None:
        try:
            saved_path = save_speech_to_mp3(
                backend=backend,
                text=text,
                voice=voice,
                sample_rate=sample_rate,
                output_path=output_path,
            )
        except Exception as exc:
            self._mp3_save_results.put((None, exc))
            return

        self._mp3_save_results.put((saved_path, None))


def create_app(
    config: AppConfig | None = None,
    *,
    ensure_download: bool = True,
    audio_player: AudioPlayer | None = None,
) -> AppRuntime:
    cfg = config or load_config()
    assets = resolve_assets(cfg, ensure_download=ensure_download)

    try:
        backend = select_backend(cfg, assets)
    except BackendSelectionError:
        # Keep the app operational when real backend cannot be initialized.
        cfg = replace(cfg, backend_mode="mock")
        backend = select_backend(cfg, assets)

    selected_audio_player = audio_player or AudioPlayer(sample_rate=cfg.sample_rate)

    runtime_holder: dict[str, AppRuntime] = {}

    def on_event(event: ControllerEvent) -> None:
        runtime = runtime_holder.get("runtime")
        if runtime is not None:
            runtime.on_controller_event(event)

    controller = PlaybackController(
        backend=backend,
        audio_player=selected_audio_player,
        on_event=on_event,
    )

    runtime = AppRuntime(
        config=cfg,
        assets=assets,
        backend=backend,
        controller=controller,
        status_message=_initial_status_message(assets=assets, backend_name=getattr(backend, "name", "unknown")),
        voice_status=_voice_status(assets=assets),
        backend_status=_backend_status(backend_name=getattr(backend, "name", "unknown")),
    )
    runtime_holder["runtime"] = runtime
    return runtime


def run() -> None:
    runtime = create_app(ensure_download=True)
    from .ui import run_kivy_ui

    run_kivy_ui(runtime)


def _initial_status_message(assets: ResolvedAssets, backend_name: str) -> str:
    if backend_name == "mock":
        if assets.errors:
            return "; ".join(assets.errors)
        if not assets.ready:
            return "Model assets unavailable. Running in mock mode until download succeeds."
    return "Ready"


def _voice_status(assets: ResolvedAssets) -> str:
    return "Voice: Available" if assets.voices_path is not None else "Voice: Missing"


def _backend_status(backend_name: str) -> str:
    display = backend_name.replace("_", " ").strip().title() if backend_name else "Unknown"
    return f"Backend: {display}"


def _default_mp3_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.home() / "Downloads" / f"kookie-{stamp}.mp3"
