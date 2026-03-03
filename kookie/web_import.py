from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.request import Request, urlopen


class WebImportError(RuntimeError):
    """Raised when webpage text extraction fails."""


@dataclass(slots=True)
class WebImportResult:
    text: str
    url: str
    title: str = ""


_SKIP_TAGS = frozenset({"script", "style", "head", "nav", "footer", "aside", "noscript"})
_BLOCK_TAGS = frozenset({
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "br", "tr", "td", "th", "blockquote",
    "section", "article", "main", "header",
})


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        lower = tag.lower()
        if lower in _SKIP_TAGS:
            self._skip_depth += 1
        if lower == "title":
            self._in_title = True
        if lower in _BLOCK_TAGS and self._skip_depth == 0:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        if lower == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._skip_depth > 0:
            return
        self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        lines = [line.rstrip() for line in raw.splitlines()]
        cleaned: list[str] = []
        blank_count = 0
        for line in lines:
            if line:
                blank_count = 0
                cleaned.append(line)
            else:
                blank_count += 1
                if blank_count <= 2:
                    cleaned.append("")
        return "\n".join(cleaned).strip()


def fetch_webpage_text(
    url: str,
    *,
    timeout: float = 15.0,
    opener=None,
) -> WebImportResult:
    """Fetch a webpage and return its readable text content."""
    normalized = _normalize_url(url)

    req = Request(
        normalized,
        headers={"User-Agent": "Mozilla/5.0 (compatible; kookie-tts/1.0)"},
    )

    try:
        _open = opener if opener is not None else urlopen
        with _open(req, timeout=timeout) as response:
            content_type = (response.headers or {}).get("Content-Type", "") or ""
            charset = _parse_charset(content_type) or "utf-8"
            raw_bytes = response.read()
    except URLError as exc:
        raise WebImportError(f"Unable to fetch URL: {exc.reason}") from exc
    except Exception as exc:
        raise WebImportError(f"Unable to fetch URL: {exc}") from exc

    try:
        html = raw_bytes.decode(charset, errors="replace")
    except LookupError:
        html = raw_bytes.decode("utf-8", errors="replace")

    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()

    if not text:
        raise WebImportError("No readable text found on the page.")

    return WebImportResult(text=text, url=normalized, title=extractor.title)


def _normalize_url(url: str) -> str:
    stripped = url.strip()
    if not stripped:
        raise WebImportError("URL cannot be empty.")
    if not stripped.startswith(("http://", "https://")):
        stripped = "https://" + stripped
    return stripped


def _parse_charset(content_type: str) -> str | None:
    for part in content_type.split(";"):
        stripped = part.strip()
        if stripped.lower().startswith("charset="):
            value = stripped[8:].strip().strip('"').strip("'")
            return value or None
    return None
