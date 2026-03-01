import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kookie.app import create_app
from kookie.config import AppConfig
import kookie.pdf_import


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


@pytest.mark.integration
def test_ocr_import_integration_flow(tmp_path: Path, monkeypatch) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    
    target_pdf = tmp_path / "scanned_doc.pdf"
    target_pdf.write_bytes(b"fake-pdf-content")
    
    # Mocking components to simulate a scanned PDF
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_pixmap = MagicMock()
    
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    
    # Simulate no text on the page
    mock_page.get_text.return_value = ""
    mock_page.get_pixmap.return_value = mock_pixmap
    mock_pixmap.tobytes.return_value = b"fake-png-data"
    
    # Use monkeypatch to override functions in pdf_import module
    mock_pymupdf = MagicMock()
    mock_pymupdf.open.return_value = mock_doc
    
    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda name: mock_pymupdf if name == "pymupdf" else MagicMock())
    monkeypatch.setattr("kookie.pdf_import.perform_ocr_on_image_bytes", lambda _: "Extracted from OCR")
    
    # Start async load
    assert runtime.start_pdf_load(target_pdf) is True
    
    # Wait for completion
    deadline = time.time() + 2.0
    text = None
    while time.time() < deadline:
        text, _ = runtime.poll_pdf_load()
        if text:
            break
        time.sleep(0.05)
        
    assert text == "Extracted from OCR"
    assert runtime.text == "Extracted from OCR"
    assert "Loaded PDF (with OCR)" in runtime.status_message
    assert runtime.metrics.snapshot()["pdf_loaded"] == 1
