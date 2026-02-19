from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

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


def test_save_mp3_shows_categorized_filesystem_error(tmp_path: Path, monkeypatch) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("save this")

    def _raise_permission(**_kwargs):
        raise PermissionError("cannot write output")

    monkeypatch.setattr("kookie.app.save_speech_to_mp3", _raise_permission)

    runtime.save_mp3(output_path=tmp_path / "out.mp3")

    assert "FS-002" in runtime.status_message
    assert "Hint:" in runtime.status_message


def test_load_pdf_shows_categorized_network_error(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    def _loader(_path: Path) -> str:
        raise URLError("offline")

    runtime.load_pdf(tmp_path / "notes.pdf", loader=_loader)

    assert "NET-001" in runtime.status_message
    assert "Hint:" in runtime.status_message
