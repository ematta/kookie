from __future__ import annotations

from pathlib import Path

from kookie.pdf_import import extract_pdf_content


class _Page:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self, mode: str) -> str:
        assert mode == "text"
        return self._text


class _Document:
    def __init__(self, pages: list[str], metadata: dict[str, str] | None = None) -> None:
        self._pages = [_Page(text) for text in pages]
        self.metadata = metadata or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __iter__(self):
        return iter(self._pages)

    def __len__(self) -> int:
        return len(self._pages)

    def __getitem__(self, idx: int):
        return self._pages[idx]


def test_extract_pdf_content_returns_metadata_and_selected_pages(monkeypatch) -> None:
    class _PyMuPDF:
        @staticmethod
        def open(path: str):
            assert path == "/tmp/sample.pdf"
            return _Document(
                ["Page one", "Page two", "Page three"],
                metadata={"title": "My Doc", "author": "Author A"},
            )

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda _: _PyMuPDF())

    result = extract_pdf_content("/tmp/sample.pdf", page_numbers=[2, 3])

    assert result.text == "Page two\n\nPage three"
    assert result.metadata["title"] == "My Doc"
    assert result.metadata["author"] == "Author A"
    assert result.pages_loaded == [2, 3]
    assert result.used_ocr is False


def test_extract_pdf_content_uses_ocr_fallback_when_text_is_missing(monkeypatch) -> None:
    class _PyMuPDF:
        @staticmethod
        def open(path: str):
            assert path == "/tmp/scanned.pdf"
            return _Document(["", " "], metadata={"title": "Scan"})

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda _: _PyMuPDF())

    result = extract_pdf_content(
        Path("/tmp/scanned.pdf"),
        use_ocr_fallback=True,
        ocr_loader=lambda path: f"OCR:{Path(path).name}",
    )

    assert result.text == "OCR:scanned.pdf"
    assert result.used_ocr is True


def test_extract_pdf_content_emits_progress(monkeypatch) -> None:
    class _PyMuPDF:
        @staticmethod
        def open(path: str):
            assert path == "/tmp/sample.pdf"
            return _Document(["A", "B", "C"])

    events: list[tuple[int, int]] = []

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda _: _PyMuPDF())

    extract_pdf_content(
        "/tmp/sample.pdf",
        progress_callback=lambda current, total: events.append((current, total)),
    )

    assert events[-1] == (3, 3)
