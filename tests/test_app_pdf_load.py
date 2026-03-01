import time
from pathlib import Path
from unittest.mock import MagicMock

from kookie.app import create_app
from kookie.config import AppConfig
from kookie.pdf_import import PdfImportResult


class _AudioPlayer:
    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return


def test_load_pdf_updates_text_and_status_on_success(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("before")
    target = tmp_path / "notes.pdf"
    capture: dict[str, Path] = {}

    def _loader(path: Path, **kwargs) -> PdfImportResult:
        capture["path"] = path
        return PdfImportResult(text="Imported from PDF", pages_loaded=[1])

    loaded = runtime.load_pdf(target, loader=_loader)

    assert loaded == "Imported from PDF"
    assert capture["path"] == target
    assert runtime.text == "Imported from PDF"
    assert runtime.status_message == "Loaded PDF: notes.pdf"


def test_load_pdf_updates_status_with_ocr_flag(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    target = tmp_path / "scanned.pdf"

    def _loader(path: Path, **kwargs) -> PdfImportResult:
        return PdfImportResult(text="OCR Text", pages_loaded=[1], used_ocr=True)

    runtime.load_pdf(target, loader=_loader)

    assert runtime.text == "OCR Text"
    assert runtime.status_message == "Loaded PDF (with OCR): scanned.pdf"


def test_load_pdf_keeps_existing_text_on_failure(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    runtime.set_text("Existing text")
    original = runtime.text

    def _loader(_path: Path, **kwargs) -> PdfImportResult:
        raise RuntimeError("invalid or encrypted PDF")

    loaded = runtime.load_pdf(tmp_path / "broken.pdf", loader=_loader)

    assert loaded is None
    assert runtime.text == original
    assert runtime.status_message.startswith("Unable to load PDF:")
    assert "invalid or encrypted PDF" in runtime.status_message


def test_async_pdf_load_flow(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )
    target = tmp_path / "async.pdf"

    def _slow_loader(path: Path, **kwargs) -> PdfImportResult:
        time.sleep(0.1)
        return PdfImportResult(text="Async Content", pages_loaded=[1])

    assert runtime.start_pdf_load(target, loader=_slow_loader) is True
    assert runtime.is_loading_pdf is True
    assert "Loading PDF: async.pdf" in runtime.status_message

    # Wait for completion
    deadline = time.time() + 2.0
    text, path = None, None
    while time.time() < deadline:
        text, path = runtime.poll_pdf_load()
        if text is not None:
            break
        time.sleep(0.05)

    assert text == "Async Content"
    assert path == target
    assert runtime.text == "Async Content"
    assert runtime.is_loading_pdf is False
    assert runtime.status_message == "Loaded PDF: async.pdf"
