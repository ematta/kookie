import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kookie.pdf_import import extract_pdf_content


@pytest.mark.perf
def test_pdf_import_performance_standard_text() -> None:
    # Simulate a multi-page PDF with lots of text
    mock_doc = MagicMock()
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.__len__.return_value = 50  # 50 pages
    
    pages = []
    for i in range(50):
        page = MagicMock()
        page.get_text.return_value = f"Page content {i} " * 100
        pages.append(page)
        
    mock_doc.__getitem__.side_effect = lambda idx: pages[idx]
    
    with patch("importlib.import_module") as mock_import:
        mock_pymupdf = MagicMock()
        mock_pymupdf.open.return_value = mock_doc
        mock_import.return_value = mock_pymupdf
        
        start_time = time.time()
        result = extract_pdf_content("fake.pdf", use_ocr_fallback=True)
        end_time = time.time()
        
        duration = end_time - start_time
        # Even with 50 pages and OCR checks (which should be fast if text is found), 
        # it should be very quick.
        assert duration < 0.5  # 500ms limit for 50 pages of mock extraction
        assert len(result.text) > 0
        assert result.used_ocr is False
