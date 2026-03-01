from unittest.mock import MagicMock
import pytest
from kookie.pdf_import import is_page_scanned

def test_is_page_scanned_returns_true_for_empty_text():
    # Mock a PyMuPDF page with no text
    mock_page = MagicMock()
    mock_page.get_text.return_value = ""
    
    assert is_page_scanned(mock_page) is True

def test_is_page_scanned_returns_false_for_non_empty_text():
    # Mock a PyMuPDF page with some text
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Hello World"
    
    assert is_page_scanned(mock_page) is False

def test_is_page_scanned_returns_true_for_whitespace_only_text():
    # Mock a PyMuPDF page with only whitespace
    mock_page = MagicMock()
    mock_page.get_text.return_value = "  \n\t  "
    
    assert is_page_scanned(mock_page) is True
