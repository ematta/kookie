from kookie.app import create_app
from kookie.config import AppConfig
from kookie.controller import PlaybackState


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


def test_create_app_mock_backend_smoke(tmp_path) -> None:
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path)
    runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    runtime.set_text("Hello from smoke test.")
    assert runtime.text == "Hello from smoke test."

    assert runtime.play() is True
    runtime.wait_until_idle(timeout=2.0)

    assert runtime.controller.state in {PlaybackState.IDLE, PlaybackState.ERROR}


def test_create_app_applies_audio_queue_timeout_from_config(tmp_path) -> None:
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path, audio_queue_timeout=0.35)
    runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    assert runtime.controller._queue_timeout == 0.35


def test_runtime_shutdown_closes_health_server_once(tmp_path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    class _FakeServer:
        def __init__(self) -> None:
            self.shutdown_calls = 0
            self.close_calls = 0

        def shutdown(self) -> None:
            self.shutdown_calls += 1

        def server_close(self) -> None:
            self.close_calls += 1

    fake_server = _FakeServer()
    runtime._health_server = fake_server

    runtime.shutdown()
    runtime.shutdown()

    assert fake_server.shutdown_calls == 1
    assert fake_server.close_calls == 1
