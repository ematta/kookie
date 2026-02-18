from pathlib import Path

from kookie.app import create_app
from kookie.config import AppConfig


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


def test_play_requires_text_area_input(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    assert runtime.play() is False
    assert runtime.status_message == "Enter text in the text area."
