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


def test_save_mp3_requires_text(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    assert runtime.save_mp3(output_path=tmp_path / "speech.mp3") is None
    assert runtime.status_message == "Enter text in the text area."


def test_save_mp3_updates_status_on_success(tmp_path: Path, monkeypatch) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("Save this speech")
    output_path = tmp_path / "saved.mp3"

    def _fake_save_speech_to_mp3(**kwargs):
        kwargs["output_path"].write_bytes(b"mp3")
        return kwargs["output_path"]

    monkeypatch.setattr("kookie.app.save_speech_to_mp3", _fake_save_speech_to_mp3)

    assert runtime.save_mp3(output_path=output_path) == output_path
    assert runtime.status_message == f"Saved MP3: {output_path}"


def test_save_mp3_updates_status_on_failure(tmp_path: Path, monkeypatch) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("Save this speech")

    def _fake_save_speech_to_mp3(**kwargs):
        raise RuntimeError("ffmpeg is required")

    monkeypatch.setattr("kookie.app.save_speech_to_mp3", _fake_save_speech_to_mp3)

    assert runtime.save_mp3(output_path=tmp_path / "saved.mp3") is None
    assert runtime.status_message == "Unable to save MP3: ffmpeg is required"
