from unittest.mock import patch

from conftest import _AudioPlayer

from kookie.app import create_app
from kookie.config import AppConfig
from kookie.controller import PlaybackState


def test_create_app_mock_backend_smoke(tmp_path) -> None:
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path)
    runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    runtime.set_text("Hello from smoke test.")
    assert runtime.text == "Hello from smoke test."

    assert runtime.play() is True
    runtime.wait_until_idle(timeout=2.0)

    assert runtime.controller.state is PlaybackState.IDLE


def test_create_app_applies_audio_queue_timeout_from_config(tmp_path) -> None:
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path, audio_queue_timeout=0.35)
    runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    assert runtime.controller.queue_timeout == 0.35


def test_runtime_shutdown_closes_health_server_once(tmp_path) -> None:
    class _FakeServer:
        def __init__(self) -> None:
            self.shutdown_calls = 0
            self.close_calls = 0

        def shutdown(self) -> None:
            self.shutdown_calls += 1

        def server_close(self) -> None:
            self.close_calls += 1

    fake_server = _FakeServer()
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path, health_check_enabled=True)
    with patch("kookie.app.start_health_server", return_value=fake_server):
        runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    runtime.shutdown()
    runtime.shutdown()

    assert fake_server.shutdown_calls == 1
    assert fake_server.close_calls == 1
