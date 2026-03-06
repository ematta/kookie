from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kookie.web_import import (
    WebImportError,
    WebImportResult,
    _normalize_url,
    _parse_charset,
    fetch_webpage_text,
)


def _make_response(html: str, charset: str = "utf-8", content_type: str | None = None) -> MagicMock:
    raw = html.encode(charset, errors="replace")
    resp = MagicMock()
    resp.read.return_value = raw
    ct = content_type or f"text/html; charset={charset}"
    resp.headers = {"Content-Type": ct}
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _opener(response: MagicMock):
    def _open(req, timeout=None):
        return response

    return _open


# --- _normalize_url ---


def test_normalize_url_adds_https_prefix():
    assert _normalize_url("example.com") == "https://example.com"


def test_normalize_url_keeps_https():
    assert _normalize_url("https://example.com") == "https://example.com"


def test_normalize_url_keeps_http():
    assert _normalize_url("http://example.com") == "http://example.com"


def test_normalize_url_strips_whitespace():
    assert _normalize_url("  example.com  ") == "https://example.com"


def test_normalize_url_empty_raises():
    with pytest.raises(WebImportError, match="empty"):
        _normalize_url("   ")


# --- _parse_charset ---


def test_parse_charset_returns_charset():
    assert _parse_charset("text/html; charset=utf-8") == "utf-8"


def test_parse_charset_returns_none_when_absent():
    assert _parse_charset("text/html") is None


def test_parse_charset_strips_quotes():
    assert _parse_charset('text/html; charset="iso-8859-1"') == "iso-8859-1"


# --- fetch_webpage_text ---


def test_fetch_extracts_paragraph_text():
    html = "<html><body><p>Hello world</p></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert isinstance(result, WebImportResult)
    assert "Hello world" in result.text
    assert result.url == "https://example.com"


def test_fetch_skips_script_content():
    html = "<html><body><p>Visible</p><script>var x = 1;</script></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert "Visible" in result.text
    assert "var x" not in result.text


def test_fetch_skips_style_content():
    html = "<html><head><style>body { color: red; }</style></head><body><p>Content</p></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert "Content" in result.text
    assert "color" not in result.text


def test_fetch_extracts_title():
    html = "<html><head><title>My Page</title></head><body><p>Text</p></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert result.title == "My Page"


def test_fetch_prepends_https_if_missing():
    html = "<html><body><p>Content</p></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("example.com", opener=_opener(response))
    assert result.url == "https://example.com"


def test_fetch_empty_page_raises():
    html = "<html><body></body></html>"
    response = _make_response(html)
    with pytest.raises(WebImportError, match="No readable text"):
        fetch_webpage_text("https://example.com", opener=_opener(response))


def test_fetch_network_error_raises():
    from urllib.error import URLError

    def _failing_opener(req, timeout=None):
        raise URLError("Connection refused")

    with pytest.raises(WebImportError, match="Unable to fetch URL"):
        fetch_webpage_text("https://example.com", opener=_failing_opener)


def test_fetch_generic_error_raises():
    def _failing_opener(req, timeout=None):
        raise OSError("Network unreachable")

    with pytest.raises(WebImportError, match="Unable to fetch URL"):
        fetch_webpage_text("https://example.com", opener=_failing_opener)


def test_fetch_nav_content_skipped():
    html = "<html><body><nav>Menu items</nav><main><p>Article text</p></main></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert "Article text" in result.text
    assert "Menu items" not in result.text


def test_fetch_heading_text_included():
    html = "<html><body><h1>Big Heading</h1><p>Body text</p></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert "Big Heading" in result.text
    assert "Body text" in result.text


def test_fetch_handles_charset_from_headers():
    html = "<html><body><p>Caf\u00e9</p></body></html>"
    response = _make_response(html, charset="utf-8", content_type="text/html; charset=utf-8")
    result = fetch_webpage_text("https://example.com", opener=_opener(response))
    assert "Caf\u00e9" in result.text


def test_fetch_result_url_is_normalised():
    html = "<html><body><p>Text</p></body></html>"
    response = _make_response(html)
    result = fetch_webpage_text("  example.com/path  ", opener=_opener(response))
    assert result.url.startswith("https://")


def test_fetch_empty_url_raises():
    with pytest.raises(WebImportError, match="empty"):
        fetch_webpage_text("", opener=lambda req, timeout=None: None)
