from unittest.mock import MagicMock, patch
import pytest
from kookie.pdf_import import get_page_image_bytes, perform_ocr_on_image_bytes

def test_get_page_image_bytes_calls_pixmap_methods():
    # Mock a PyMuPDF page
    mock_page = MagicMock()
    mock_pixmap = MagicMock()
    mock_page.get_pixmap.return_value = mock_pixmap
    mock_pixmap.tobytes.return_value = b"fake-image-data"
    
    result = get_page_image_bytes(mock_page)
    
    assert result == b"fake-image-data"
    mock_page.get_pixmap.assert_called_once()
    mock_pixmap.tobytes.assert_called_once_with("png")

def test_perform_ocr_on_image_bytes_calls_tesseract():
    image_bytes = b"fake-png-bytes"
    expected_text = "Extracted OCR Text"
    
    with patch("PIL.Image.open") as mock_open, \
         patch("pytesseract.image_to_string") as mock_ocr:
        
        mock_image = MagicMock()
        mock_open.return_value = mock_image
        mock_ocr.return_value = expected_text
        
        result = perform_ocr_on_image_bytes(image_bytes)
        
        assert result == expected_text
        # io.BytesIO(image_bytes) is called inside
        mock_ocr.assert_called_once_with(mock_image)
