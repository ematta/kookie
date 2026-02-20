from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import TypedDict

from .assets import ResolvedAssets, resolve_assets
from .audio import AudioPlayer
from .backends import BackendSelectionError, select_backend
from .config import AppConfig, load_config
from .controller import ControllerEvent, PlaybackController
from .errors import classify_exception, to_user_message
from .export import save_speech_to_mp3
from .monitoring import HealthStatus, MetricsStore, start_health_server
from .pdf_import import extract_pdf_text
from .preload import preload_assets
from .telemetry import LocalTelemetry
from .text_processing import normalize_text
from .update_checker import UpdateInfo, check_for_update


class StartupPrompt(TypedDict):
    title: str
    message: str
    can_retry: bool
    actions: tuple[str, ...]


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
    selected_voice: str = "af_sarah"
    _mp3_save_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _mp3_save_thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _mp3_save_results: queue.Queue[tuple[Path | None, Exception | None]] = field(
        default_factory=queue.Queue,
        init=False,
        repr=False,
    )
    _is_saving_mp3: bool = field(default=False, init=False, repr=False)
    telemetry: LocalTelemetry | None = field(default=None, repr=False)
    metrics: MetricsStore = field(default_factory=MetricsStore, repr=False)
    _health_server: object | None = field(default=None, init=False, repr=False)

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
            self.metrics.increment("play_rejected_empty_text")
            return False

        started = self.controller.start(self.text, voice=self.selected_voice)
        if not started:
            self.status_message = "Playback is already running."
            self.metrics.increment("play_rejected")
            if self.telemetry is not None:
                self.telemetry.record("play_rejected", {"reason": "already_running"})
            return False
        self.metrics.increment("play_started")
        if self.telemetry is not None:
            self.telemetry.record("play_started", {"voice": self.selected_voice, "text_len": len(self.text)})
        return started

    def stop(self) -> bool:
        stopped = self.controller.stop()
        if stopped:
            self.metrics.increment("play_stopped")
        if self.telemetry is not None:
            self.telemetry.record("play_stopped", {"stopped": stopped})
        return stopped

    def save_mp3(self, output_path: Path | None = None) -> Path | None:
        if not self.text:
            self.status_message = "Enter text in the text area."
            return None

        selected_output = output_path or _default_mp3_output_path()
        try:
            saved_path = save_speech_to_mp3(
                backend=self.backend,
                text=self.text,
                voice=self.selected_voice,
                sample_rate=self.config.sample_rate,
                output_path=selected_output,
            )
        except Exception as exc:
            error = classify_exception(exc)
            self.status_message = f"Unable to save MP3: {to_user_message(error)}"
            self.metrics.increment("save_mp3_failed")
            if self.telemetry is not None:
                self.telemetry.record(
                    "save_mp3_failed",
                    {"error_code": error.code.value, "category": error.category.value},
                )
            return None

        self.status_message = f"Saved MP3: {saved_path}"
        self.metrics.increment("save_mp3_completed")
        if self.telemetry is not None:
            self.telemetry.record("save_mp3_completed", {"path": str(saved_path)})
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
                    "voice": self.selected_voice,
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
            categorized = classify_exception(error)
            self.status_message = f"Unable to save MP3: {to_user_message(categorized)}"
            self.metrics.increment("save_mp3_failed")
            if self.telemetry is not None:
                self.telemetry.record(
                    "save_mp3_failed",
                    {"error_code": categorized.code.value, "category": categorized.category.value},
                )
            return

        if saved_path is not None:
            self.status_message = f"Saved MP3: {saved_path}"
            self.metrics.increment("save_mp3_completed")
            if self.telemetry is not None:
                self.telemetry.record("save_mp3_completed", {"path": str(saved_path)})
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
            error = classify_exception(exc)
            self.status_message = f"Unable to load PDF: {to_user_message(error)}"
            self.metrics.increment("pdf_load_failed")
            if self.telemetry is not None:
                self.telemetry.record(
                    "pdf_load_failed",
                    {"error_code": error.code.value, "category": error.category.value},
                )
            return None

        self.set_text(text)
        self.status_message = f"Loaded PDF: {pdf_path.name}"
        self.metrics.increment("pdf_loaded")
        if self.telemetry is not None:
            self.telemetry.record("pdf_loaded", {"path": str(pdf_path), "text_len": len(self.text)})
        return text

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        self.controller.wait_until_idle(timeout=timeout)

    def shutdown(self) -> None:
        try:
            self.stop()
            self.wait_until_idle(timeout=0.2)
        except Exception:
            pass

        server = self._health_server
        if server is None:
            return

        self._health_server = None
        shutdown_server = getattr(server, "shutdown", None)
        if callable(shutdown_server):
            try:
                shutdown_server()
            except Exception:
                pass
        close_server = getattr(server, "server_close", None)
        if callable(close_server):
            try:
                close_server()
            except Exception:
                pass

    def pause(self) -> bool:
        return self.controller.pause()

    def resume(self) -> bool:
        return self.controller.resume()

    def seek(self, *, seconds: float) -> bool:
        return self.controller.seek(seconds=seconds)

    def set_volume(self, value: float) -> float:
        return self.controller.set_volume(value)

    def set_playback_speed(self, value: float) -> float:
        return self.controller.set_playback_speed(value)

    @property
    def playback_progress(self) -> dict[str, int]:
        return self.controller.progress

    def set_voice(self, voice: str) -> str:
        selected = voice.strip() if isinstance(voice, str) else ""
        if not selected:
            selected = self.config.default_voice
        self.selected_voice = selected
        return self.selected_voice

    def available_voices(self) -> list[str]:
        provider = getattr(self.backend, "list_voices", None)
        if callable(provider):
            try:
                values = provider()
            except Exception:
                values = []
            voices = [str(item).strip() for item in values if str(item).strip()]
            if voices:
                return voices
        return [self.config.default_voice]

    def check_for_updates(
        self,
        *,
        checker: Callable[..., UpdateInfo | None] = check_for_update,
    ) -> UpdateInfo | None:
        if not getattr(self.config, "update_check_enabled", True):
            return None

        try:
            info = checker(
                current_version=_current_app_version(),
                repo=self.config.update_repo,
            )
        except Exception as exc:
            categorized = classify_exception(exc)
            self.status_message = f"Unable to check for updates: {to_user_message(categorized)}"
            self.metrics.increment("update_check_failed")
            if self.telemetry is not None:
                self.telemetry.record(
                    "update_check_failed",
                    {"error_code": categorized.code.value, "category": categorized.category.value},
                )
            return None

        if info is None:
            return None

        self.status_message = f"Update available: {info.version} ({info.url})"
        if self.telemetry is not None:
            self.telemetry.record("update_available", {"version": info.version, "url": info.url})
        return info

    def health_status(self) -> HealthStatus:
        return HealthStatus(
            status="ok" if self.assets.ready else "degraded",
            backend=self.backend_name,
            assets_ready=self.assets.ready,
            details={
                "state": self.controller.state.value,
                "metrics": self.metrics.snapshot(),
            },
        )

    @property
    def backend_name(self) -> str:
        return getattr(self.backend, "name", self.backend.__class__.__name__.lower())

    def on_controller_event(self, event: ControllerEvent) -> None:
        if event.kind == "error":
            error = classify_exception(RuntimeError(event.message))
            self.status_message = f"Speech generation failed: {to_user_message(error)}"
            self.metrics.increment("playback_error")
            if self.telemetry is not None:
                self.telemetry.record(
                    "playback_error",
                    {"error_code": error.code.value, "category": error.category.value},
                )
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
        queue_timeout=cfg.audio_queue_timeout,
    )

    runtime = AppRuntime(
        config=cfg,
        assets=assets,
        backend=backend,
        controller=controller,
        status_message=_initial_status_message(assets=assets, backend_name=getattr(backend, "name", "unknown")),
        voice_status=_voice_status(assets=assets),
        backend_status=_backend_status(backend_name=getattr(backend, "name", "unknown")),
        selected_voice=cfg.default_voice,
        telemetry=LocalTelemetry(
            enabled=bool(getattr(cfg, "telemetry_enabled", False)),
            output_path=Path(getattr(cfg, "telemetry_file", cfg.asset_dir / "telemetry.jsonl")).expanduser(),
        ),
    )
    runtime_holder["runtime"] = runtime
    if getattr(cfg, "health_check_enabled", False):
        runtime._health_server = start_health_server(
            host=cfg.health_check_host,
            port=cfg.health_check_port,
            health_provider=runtime.health_status,
            metrics_store=runtime.metrics,
        )
    return runtime


def run() -> None:
    from .ui import run_kivy_ui

    config = load_config()
    while True:
        preload_result = preload_assets(config)

        startup_prompt: StartupPrompt | None = None
        runtime_config = config
        if not preload_result.ready:
            runtime_config = replace(config, backend_mode="mock")
            startup_prompt = {
                "title": "Assets unavailable",
                "message": preload_result.message,
                "can_retry": True,
                "actions": ("continue_mock", "retry", "quit"),
            }

        runtime = create_app(runtime_config, ensure_download=False)
        try:
            action = run_kivy_ui(runtime, startup_prompt=startup_prompt)
        finally:
            shutdown = getattr(runtime, "shutdown", None)
            if callable(shutdown):
                shutdown()

        if startup_prompt is None:
            return

        if action == "retry":
            continue

        return


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


def _current_app_version() -> str:
    try:
        return package_version("kookie")
    except PackageNotFoundError:
        return "0.1.0"
