from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from .assets import ResolvedAssets, resolve_assets
from .audio import AudioPlayer
from .backends import BackendSelectionError, select_backend
from .clipboard import ClipboardMonitor
from .config import AppConfig, load_config
from .controller import ControllerEvent, PlaybackController
from .text_processing import normalize_text


@dataclass(slots=True)
class AppRuntime:
    config: AppConfig
    assets: ResolvedAssets
    backend: object
    controller: PlaybackController
    clipboard_monitor: ClipboardMonitor
    text: str = ""
    status_message: str = "Ready"

    def set_text(self, value: str) -> None:
        self.text = normalize_text(value)

    def play(self) -> bool:
        if not self.text:
            self.status_message = "Enter text or copy text to the clipboard."
            return False

        started = self.controller.start(self.text, voice=self.config.default_voice)
        if not started:
            self.status_message = "Playback is already running."
        return started

    def stop(self) -> bool:
        return self.controller.stop()

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        self.controller.wait_until_idle(timeout=timeout)

    def poll_clipboard_once(self) -> str | None:
        return self.clipboard_monitor.poll_once()

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
    read_clipboard: Callable[[], str] | None = None,
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

    reader = read_clipboard or _default_clipboard_reader
    monitor = ClipboardMonitor(
        read_clipboard=reader,
        on_new_text=lambda value: runtime_holder["runtime"].set_text(value),
        poll_interval=cfg.clipboard_poll_interval,
    )

    runtime = AppRuntime(
        config=cfg,
        assets=assets,
        backend=backend,
        controller=controller,
        clipboard_monitor=monitor,
        status_message=_initial_status_message(assets=assets, backend_name=getattr(backend, "name", "unknown")),
    )
    runtime_holder["runtime"] = runtime
    return runtime


def run() -> None:
    runtime = create_app(ensure_download=True)
    from .ui import run_kivy_ui

    run_kivy_ui(runtime)


def _default_clipboard_reader() -> str:
    try:
        from kivy.core.clipboard import Clipboard  # type: ignore

        value = Clipboard.paste()
        return value if isinstance(value, str) else ""
    except Exception:
        return ""


def _initial_status_message(assets: ResolvedAssets, backend_name: str) -> str:
    if backend_name == "mock":
        if assets.errors:
            return "; ".join(assets.errors)
        if not assets.ready:
            return "Model assets unavailable. Running in mock mode until download succeeds."
    return "Ready"
