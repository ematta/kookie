from kookie.clipboard import ClipboardMonitor


def test_clipboard_monitor_deduplicates_text() -> None:
    values = iter(["hello", "hello", "world"])

    def reader() -> str:
        return next(values)

    seen = []
    monitor = ClipboardMonitor(read_clipboard=reader, on_new_text=seen.append, poll_interval=0.5)

    monitor.poll_once()
    monitor.poll_once()
    monitor.poll_once()

    assert seen == ["hello", "world"]


def test_clipboard_monitor_is_paste_only() -> None:
    play_calls = []
    displayed_text = []

    monitor = ClipboardMonitor(
        read_clipboard=lambda: "new text",
        on_new_text=displayed_text.append,
        poll_interval=0.5,
    )

    monitor.poll_once()

    assert displayed_text == ["new text"]
    assert play_calls == []
