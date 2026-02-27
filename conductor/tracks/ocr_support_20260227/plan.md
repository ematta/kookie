# Track Implementation Plan - ocr_support_20260227

- [ ] **Phase 1: Foundation & Detection**
  - [ ] Task: Research OCR libraries and update `pyproject.toml`
    - [ ] Research `pytesseract` and Tesseract engine compatibility for macOS
    - [ ] Update `pyproject.toml` with new dependencies
    - [ ] Run `uv sync` to install dependencies
  - [ ] Task: Implement OCR detection in `pdf_import.py`
    - [ ] Write failing test for detecting a "text-less" PDF page
    - [ ] Implement `is_page_scanned` check in `pdf_import.py`
    - [ ] Verify tests pass and coverage >80%
  - [ ] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Detection' (Protocol in workflow.md) [checkpoint: ]

- [ ] **Phase 2: Core OCR Implementation**
  - [ ] Task: Extract images from PDF pages for OCR
    - [ ] Write failing test for image extraction from a PDF page
    - [ ] Implement image extraction logic using PyMuPDF
    - [ ] Verify tests pass and coverage >80%
  - [ ] Task: Implement OCR processing using Tesseract
    - [ ] Write failing test for processing a page image with OCR
    - [ ] Implement `perform_ocr_on_page` using `pytesseract`
    - [ ] Verify tests pass and coverage >80%
  - [ ] Task: Conductor - User Manual Verification 'Phase 2: Core OCR Implementation' (Protocol in workflow.md) [checkpoint: ]

- [ ] **Phase 3: Integration & UI Feedback**
  - [ ] Task: Update Controller and UI to handle OCR flow
    - [ ] Write failing tests for UI status updates during OCR
    - [ ] Implement background OCR processing in `controller.py`
    - [ ] Update `ui.py` to show "Performing OCR..." status messages
    - [ ] Verify tests pass and coverage >80%
  - [ ] Task: Conductor - User Manual Verification 'Phase 3: Integration & UI Feedback' (Protocol in workflow.md) [checkpoint: ]

- [ ] **Phase 4: Finalization**
  - [ ] Task: Refine and Test OCR accuracy
    - [ ] Add integration tests for end-to-end OCR PDF import
    - [ ] Verify performance regression guards
  - [ ] Task: Conductor - User Manual Verification 'Phase 4: Finalization' (Protocol in workflow.md) [checkpoint: ]
