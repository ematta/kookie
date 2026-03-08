from __future__ import annotations

import time
from pathlib import Path

from conftest import _AudioPlayer

from kookie.app import create_app
from kookie.config import AppConfig
from kookie.web_import import WebImportError, WebImportResult


def _make_fetcher(text: str = "Page content", url: str = "https://example.com", title: str = "Example"):
    def _fetcher(url_arg: str) -> WebImportResult:
        return WebImportResult(text=text, url=url, title=title)

    return _fetcher


def _make_failing_fetcher(message: str = "Connection refused"):
    def _fetcher(url_arg: str) -> WebImportResult:
        raise WebImportError(message)

    return _fetcher


def _runtime(tmp_path: Path):
    return create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )


# --- start_webpage_load ---


def test_start_webpage_load_returns_true(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    started = runtime.start_webpage_load("https://example.com", fetcher=_make_fetcher())
    assert started is True


def test_start_webpage_load_sets_status_to_loading(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.start_webpage_load("https://example.com", fetcher=_make_fetcher())
    assert runtime.status_message == "Loading URL..."


def test_start_webpage_load_sets_is_loading(tmp_path: Path) -> None:
    slow_called = []

    def _slow_fetcher(url: str) -> WebImportResult:
        time.sleep(0.15)
        slow_called.append(True)
        return WebImportResult(text="Hello", url=url, title="")

    runtime = _runtime(tmp_path)
    runtime.start_webpage_load("https://example.com", fetcher=_slow_fetcher)
    assert runtime.is_loading_webpage is True


def test_start_webpage_load_rejects_concurrent(tmp_path: Path) -> None:
    def _slow_fetcher(url: str) -> WebImportResult:
        time.sleep(0.2)
        return WebImportResult(text="Hello", url=url, title="")

    runtime = _runtime(tmp_path)
    assert runtime.start_webpage_load("https://example.com", fetcher=_slow_fetcher) is True
    assert runtime.start_webpage_load("https://other.com", fetcher=_slow_fetcher) is False
    assert "already in progress" in runtime.status_message


# --- poll_webpage_load ---


def test_poll_webpage_load_returns_none_before_complete(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    text, url = runtime.poll_webpage_load()
    assert text is None
    assert url is None


def test_poll_webpage_load_returns_text_and_url(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fetcher = _make_fetcher(text="Article content", url="https://example.com/page")
    runtime.start_webpage_load("https://example.com/page", fetcher=fetcher)

    deadline = time.time() + 2.0
    text, url = None, None
    while time.time() < deadline:
        text, url = runtime.poll_webpage_load()
        if text is not None:
            break
        time.sleep(0.02)

    assert text == "Article content"
    assert url == "https://example.com/page"


def test_poll_webpage_load_updates_runtime_text(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fetcher = _make_fetcher(text="Loaded page text")
    runtime.start_webpage_load("https://example.com", fetcher=fetcher)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        text, _ = runtime.poll_webpage_load()
        if text is not None:
            break
        time.sleep(0.02)

    assert runtime.text == "Loaded page text"


def test_poll_webpage_load_sets_status_on_success(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fetcher = _make_fetcher(url="https://example.com")
    runtime.start_webpage_load("https://example.com", fetcher=fetcher)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        text, _ = runtime.poll_webpage_load()
        if text is not None:
            break
        time.sleep(0.02)

    assert "https://example.com" in runtime.status_message
    assert runtime.status_message.startswith("Loaded URL:")


def test_poll_webpage_load_clears_is_loading_on_success(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fetcher = _make_fetcher()
    runtime.start_webpage_load("https://example.com", fetcher=fetcher)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        text, _ = runtime.poll_webpage_load()
        if text is not None:
            break
        time.sleep(0.02)

    assert runtime.is_loading_webpage is False


def test_poll_webpage_load_handles_fetch_error(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fetcher = _make_failing_fetcher("Connection refused")
    runtime.start_webpage_load("https://example.com", fetcher=fetcher)

    deadline = time.time() + 2.0
    text, url = None, None
    while time.time() < deadline:
        text, url = runtime.poll_webpage_load()
        if not runtime.is_loading_webpage:
            break
        time.sleep(0.02)

    assert text is None
    assert url is None
    assert "Unable to load URL" in runtime.status_message


def test_poll_webpage_load_clears_is_loading_on_error(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fetcher = _make_failing_fetcher()
    runtime.start_webpage_load("https://example.com", fetcher=fetcher)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        runtime.poll_webpage_load()
        if not runtime.is_loading_webpage:
            break
        time.sleep(0.02)

    assert runtime.is_loading_webpage is False


def test_poll_webpage_load_preserves_existing_text_on_error(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.set_text("Original content")
    fetcher = _make_failing_fetcher()
    runtime.start_webpage_load("https://example.com", fetcher=fetcher)

    deadline = time.time() + 2.0
    while time.time() < deadline:
        runtime.poll_webpage_load()
        if not runtime.is_loading_webpage:
            break
        time.sleep(0.02)

    assert runtime.text == "Original content"


# --- is_loading_webpage ---


def test_is_loading_webpage_false_initially(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    assert runtime.is_loading_webpage is False
