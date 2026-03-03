from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from conftest import _AudioPlayer

from kookie.app import AppRuntime
from kookie.assets import ResolvedAssets
from kookie.config import AppConfig
from kookie.controller import ControllerEvent, PlaybackController, PlaybackState


class _BackendNoVoices:
    """Backend with no list_voices method."""


class _BackendWithVoices:
    def list_voices(self) -> list[str]:
        return ["af_sarah", "af_sky", "am_adam"]


class _BackendVoicesRaises:
    def list_voices(self) -> list[str]:
        raise RuntimeError("backend unavailable")


def _make_runtime(*, assets_ready: bool = True, backend: object | None = None) -> AppRuntime:
    cfg = AppConfig(backend_mode="mock", asset_dir=Path("/tmp"))
    assets = ResolvedAssets(model_path=None, voices_path=None, ready=assets_ready)
    controller = PlaybackController(backend=MagicMock(), audio_player=_AudioPlayer())
    return AppRuntime(
        config=cfg,
        assets=assets,
        backend=backend or _BackendNoVoices(),
        controller=controller,
    )


# --- available_voices ---

def test_available_voices_returns_backend_voices() -> None:
    runtime = _make_runtime(backend=_BackendWithVoices())
    assert runtime.available_voices() == ["af_sarah", "af_sky", "am_adam"]


def test_available_voices_falls_back_to_default_when_no_list_voices() -> None:
    runtime = _make_runtime(backend=_BackendNoVoices())
    assert runtime.available_voices() == ["af_sarah"]


def test_available_voices_falls_back_to_default_when_list_voices_raises() -> None:
    runtime = _make_runtime(backend=_BackendVoicesRaises())
    assert runtime.available_voices() == ["af_sarah"]


# --- set_voice ---

def test_set_voice_valid_voice_updates_selection() -> None:
    runtime = _make_runtime()
    result = runtime.set_voice("af_sky")
    assert result == "af_sky"
    assert runtime.selected_voice == "af_sky"


def test_set_voice_empty_string_falls_back_to_config_default() -> None:
    runtime = _make_runtime()
    result = runtime.set_voice("")
    assert result == runtime.config.default_voice
    assert runtime.selected_voice == runtime.config.default_voice


def test_set_voice_whitespace_only_falls_back_to_config_default() -> None:
    runtime = _make_runtime()
    result = runtime.set_voice("   ")
    assert result == runtime.config.default_voice


# --- on_controller_event ---

def test_on_controller_event_error_updates_status_message() -> None:
    runtime = _make_runtime()
    event = ControllerEvent(kind="error", state=PlaybackState.ERROR, message="synthesis exploded")
    runtime.on_controller_event(event)
    assert "Speech generation failed" in runtime.status_message


def test_on_controller_event_idle_sets_ready() -> None:
    runtime = _make_runtime()
    event = ControllerEvent(kind="state", state=PlaybackState.IDLE)
    runtime.on_controller_event(event)
    assert runtime.status_message == "Ready"


def test_on_controller_event_playing_sets_playing() -> None:
    runtime = _make_runtime()
    event = ControllerEvent(kind="state", state=PlaybackState.PLAYING)
    runtime.on_controller_event(event)
    assert runtime.status_message == "Playing"


def test_on_controller_event_synthesizing_sets_generating_speech() -> None:
    runtime = _make_runtime()
    event = ControllerEvent(kind="state", state=PlaybackState.SYNTHESIZING)
    runtime.on_controller_event(event)
    assert runtime.status_message == "Generating speech"


def test_on_controller_event_stopping_sets_stopping() -> None:
    runtime = _make_runtime()
    event = ControllerEvent(kind="state", state=PlaybackState.STOPPING)
    runtime.on_controller_event(event)
    assert runtime.status_message == "Stopping"


# --- health_status ---

def test_health_status_ok_when_assets_ready() -> None:
    runtime = _make_runtime(assets_ready=True)
    status = runtime.health_status()
    assert status.status == "ok"
    assert status.assets_ready is True


def test_health_status_degraded_when_assets_not_ready() -> None:
    runtime = _make_runtime(assets_ready=False)
    status = runtime.health_status()
    assert status.status == "degraded"
    assert status.assets_ready is False


def test_health_status_includes_controller_state() -> None:
    runtime = _make_runtime()
    status = runtime.health_status()
    assert status.details["state"] == PlaybackState.IDLE.value
