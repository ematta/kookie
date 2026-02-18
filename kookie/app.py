from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, replace
from pathlib import Path

from .assets import ResolvedAssets, resolve_assets
from .audio import AudioPlayer
from .backends import BackendSelectionError, select_backend
from .config import AppConfig, load_config
from .controller import ControllerEvent, PlaybackController
from .export import save_speech_to_mp3
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
