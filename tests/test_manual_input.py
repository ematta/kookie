from pathlib import Path

from conftest import _AudioPlayer
from kookie.app import create_app
from kookie.config import AppConfig


def test_play_requires_text_area_input(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    assert runtime.play() is False
    assert runtime.status_message == "Enter text in the text area."
