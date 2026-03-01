# Track Specification - ocr_support_20260227

## Goal
Implement Optical Character Recognition (OCR) support for PDF imports in Kookie. This will enable users to import text from scanned documents or PDFs where text is stored as images rather than extractable text elements.

## Background
Currently, Kookie uses PyMuPDF (fitz) to extract text from PDFs. This method fails when the PDF contains only images of text (e.g., from a flatbed scanner), resulting in an empty editor.

## Proposed Solution
1. **Detection:** When a PDF page is loaded, Kookie will check if it contains any extractable text.
2. **Fallback:** If a page contains no text, Kookie will offer to (or automatically) perform OCR using a local OCR engine.
3. **OCR Engine:** Integrate `pytesseract` as a wrapper for the Tesseract OCR engine, which must be installed on the user's macOS system (e.g., via `brew install tesseract`).
4. **Integration:** The OCR process will be integrated into the existing `pdf_import.py` module and exposed through the `Controller`.
5. **UI:** Update the UI to indicate that OCR is being performed, especially for multi-page scanned documents, as this is a time-intensive process.

## Changes Required
### Dependencies
- Add `pytesseract` to `pyproject.toml`.
- Document Tesseract installation requirement in `README.md`.

### Core Logic (`kookie/pdf_import.py`)
- New function `is_page_scanned(page)` to detect text presence.
- New function `extract_page_text_ocr(page)` to render the page as an image and run OCR.

### Application Flow (`kookie/controller.py`)
- Update `load_pdf` to handle the OCR fallback logic.
- Ensure OCR is run asynchronously or with UI feedback to prevent application freezing.

### User Interface (`kookie/ui.py`)
- Provide status bar updates during the OCR process.

## Acceptance Criteria
- [ ] Successfully extract text from a scanned single-page PDF.
- [ ] Successfully extract text from a multi-page PDF containing both text and image-based pages.
- [ ] Provide clear UI feedback ("Performing OCR...") while processing.
- [ ] No regression in performance for standard text-based PDFs.
- [ ] Code coverage for new functionality meets the >80% target.
