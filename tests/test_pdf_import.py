from pathlib import Path

import pytest

from kookie.pdf_import import PdfImportError, extract_pdf_text


class _Page:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self, mode: str) -> str:
        assert mode == "text"
        return self._text


class _Document:
    def __init__(self, pages: list[str]) -> None:
        self._pages = [_Page(text) for text in pages]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def __iter__(self):
        return iter(self._pages)


def test_extract_pdf_text_joins_non_empty_pages_in_order(monkeypatch) -> None:
    class _PyMuPDF:
        @staticmethod
        def open(path: str):
            assert path == "/tmp/sample.pdf"
            return _Document(
                [
                    "\n First page\r\nline 2 \n",
                    "\n\n",
                    "Second page\rline 2\n",
                ]
            )

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda _: _PyMuPDF())

    text = extract_pdf_text(Path("/tmp/sample.pdf"))

    assert text == "First page\nline 2\n\nSecond page\nline 2"


def test_extract_pdf_text_raises_for_missing_pymupdf(monkeypatch) -> None:
    def _missing(_):
        raise ModuleNotFoundError("No module named 'pymupdf'")

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", _missing)

    with pytest.raises(PdfImportError, match="PyMuPDF is required"):
        extract_pdf_text("/tmp/sample.pdf")


def test_extract_pdf_text_raises_for_unreadable_pdf(monkeypatch) -> None:
    class _PyMuPDF:
        @staticmethod
        def open(_):
            raise RuntimeError("broken cross-reference table")

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda _: _PyMuPDF())

    with pytest.raises(PdfImportError, match="Unable to read PDF"):
        extract_pdf_text("/tmp/sample.pdf")


def test_extract_pdf_text_raises_for_empty_pdf_content(monkeypatch) -> None:
    class _PyMuPDF:
        @staticmethod
        def open(_):
            return _Document(["\n ", " \r\n\t"])

    monkeypatch.setattr("kookie.pdf_import.importlib.import_module", lambda _: _PyMuPDF())

    with pytest.raises(PdfImportError, match="No extractable text found"):
        extract_pdf_text("/tmp/empty.pdf")
