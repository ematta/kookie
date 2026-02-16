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
