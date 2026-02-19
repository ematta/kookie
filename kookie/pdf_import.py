from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


class PdfImportError(RuntimeError):
    """Raised when PDF text extraction fails."""


@dataclass(slots=True)
class PdfImportResult:
    text: str
    metadata: dict[str, str] = field(default_factory=dict)
    pages_loaded: list[int] = field(default_factory=list)
    used_ocr: bool = False


def extract_pdf_text(pdf_path: Path | str) -> str:
    return extract_pdf_content(pdf_path).text


def extract_pdf_content(
    pdf_path: Path | str,
    *,
    page_numbers: list[int] | None = None,
    use_ocr_fallback: bool = False,
    ocr_loader: Callable[[Path], str] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> PdfImportResult:
    path = Path(pdf_path).expanduser()

    try:
        pymupdf = importlib.import_module("pymupdf")
    except ModuleNotFoundError as exc:
        raise PdfImportError("PyMuPDF is required to load PDF files.") from exc

    pages: list[str] = []
    loaded_page_numbers: list[int] = []
    metadata: dict[str, str] = {}
    used_ocr = False
    try:
        with pymupdf.open(str(path)) as document:
            metadata = _normalize_metadata(getattr(document, "metadata", {}) or {})
            page_objects = _materialize_pages(document)
            page_indices = _selected_page_indices(len(page_objects), page_numbers)
            total_pages = len(page_indices)

            for current_idx, page_idx in enumerate(page_indices, start=1):
                page = page_objects[page_idx]
                text = _normalize_page_text(page.get_text("text"))
                if text:
                    pages.append(text)
                    loaded_page_numbers.append(page_idx + 1)
                if progress_callback is not None:
                    progress_callback(current_idx, total_pages)
    except Exception as exc:
        raise PdfImportError(f"Unable to read PDF: {exc}") from exc

    if not pages and use_ocr_fallback:
        selected_ocr_loader = ocr_loader or _default_ocr_loader
        try:
            ocr_text = _normalize_page_text(selected_ocr_loader(path))
        except Exception as exc:
            raise PdfImportError(f"No extractable text found in PDF and OCR failed: {exc}") from exc
        if ocr_text:
            pages = [ocr_text]
            used_ocr = True

    if not pages:
        raise PdfImportError("No extractable text found in PDF.")

    return PdfImportResult(
        text="\n\n".join(pages),
        metadata=metadata,
        pages_loaded=loaded_page_numbers,
        used_ocr=used_ocr,
    )


def _normalize_page_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(line.rstrip() for line in lines).strip()


def _selected_page_indices(total: int, page_numbers: list[int] | None) -> list[int]:
    if total <= 0:
        return []
    if not page_numbers:
        return list(range(total))

    selected: list[int] = []
    for raw in page_numbers:
        if raw < 1:
            continue
        idx = raw - 1
        if idx >= total:
            continue
        if idx not in selected:
            selected.append(idx)
    return selected


def _materialize_pages(document: object) -> list[object]:
    try:
        total = len(document)  # type: ignore[arg-type]
        return [document[idx] for idx in range(total)]  # type: ignore[index]
    except Exception:
        return list(document)  # type: ignore[arg-type]


def _normalize_metadata(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}

    metadata: dict[str, str] = {}
    for key in ("title", "author", "subject", "keywords", "creator", "producer"):
        value = payload.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            metadata[key] = cleaned
    return metadata


def _default_ocr_loader(path: Path) -> str:
    try:
        docling = importlib.import_module("docling.document_converter")
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise PdfImportError("Docling OCR fallback is unavailable. Install docling to enable OCR.") from exc

    converter_cls = getattr(docling, "DocumentConverter", None)
    if converter_cls is None:
        raise PdfImportError("Docling OCR fallback is unavailable due to missing DocumentConverter.")

    converter = converter_cls()
    result = converter.convert(str(path))
    document = getattr(result, "document", None)
    if document is None:
        return ""
    exporter = getattr(document, "export_to_markdown", None)
    if callable(exporter):
        return str(exporter())
    return str(document)
