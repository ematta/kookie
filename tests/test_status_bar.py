from pathlib import Path

from kookie.app import create_app
from kookie.config import AppConfig
from kookie.controller import ControllerEvent, PlaybackState


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


def test_status_bar_first_item_reports_missing_voice(tmp_path: Path) -> None:
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path)
    runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    assert runtime.status_bar_items[0] == "Voice: Missing"


def test_status_bar_first_item_reports_available_voice(tmp_path: Path) -> None:
    cfg = AppConfig(backend_mode="mock", asset_dir=tmp_path)
    (tmp_path / cfg.voices_filename).write_bytes(b"voice")

    runtime = create_app(cfg, ensure_download=False, audio_player=_AudioPlayer())

    assert runtime.status_bar_items[0] == "Voice: Available"


def test_status_bar_updates_activity_state() -> None:
    runtime = create_app(AppConfig(backend_mode="mock"), ensure_download=False, audio_player=_AudioPlayer())

    runtime.on_controller_event(ControllerEvent(kind="state", state=PlaybackState.PLAYING, message=""))

    assert runtime.status_bar_items[2] == "State: Playing"
    assert runtime.status_bar_text.startswith("Voice:")
