from __future__ import annotations

from pathlib import Path

import pytest

from conftest import _AudioPlayer
from kookie.app import create_app
from kookie.config import AppConfig
from kookie.pdf_import import PdfImportResult


@pytest.mark.integration
def test_e2e_load_play_export_workflow(tmp_path: Path, monkeypatch) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    loaded = runtime.load_pdf(
        tmp_path / "notes.pdf", 
        loader=lambda *_, **__: PdfImportResult(text="One sentence. Two sentence.", pages_loaded=[1])
    )
    assert loaded == "One sentence. Two sentence."

    assert runtime.play() is True
    runtime.wait_until_idle(timeout=2.0)

    export_path = tmp_path / "speech.mp3"

    def _fake_save_speech_to_mp3(**kwargs):
        kwargs["output_path"].write_bytes(b"fake-mp3")
        return kwargs["output_path"]

    monkeypatch.setattr("kookie.app.save_speech_to_mp3", _fake_save_speech_to_mp3)

    saved = runtime.save_mp3(output_path=export_path)
    assert saved == export_path
    assert export_path.exists()
