from unittest.mock import MagicMock
import pytest
from kookie.pdf_import import get_page_image_bytes

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
