from __future__ import annotations

import importlib
from pathlib import Path


class PdfImportError(RuntimeError):
    """Raised when PDF text extraction fails."""


def extract_pdf_text(pdf_path: Path | str) -> str:
    path = Path(pdf_path).expanduser()

    try:
        pymupdf = importlib.import_module("pymupdf")
    except ModuleNotFoundError as exc:
        raise PdfImportError("PyMuPDF is required to load PDF files.") from exc

    pages: list[str] = []
    try:
        with pymupdf.open(str(path)) as document:
            for page in document:
                text = _normalize_page_text(page.get_text("text"))
                if text:
                    pages.append(text)
    except Exception as exc:
        raise PdfImportError(f"Unable to read PDF: {exc}") from exc

    if not pages:
        raise PdfImportError("No extractable text found in PDF.")

    return "\n\n".join(pages)


def _normalize_page_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(line.rstrip() for line in lines).strip()
