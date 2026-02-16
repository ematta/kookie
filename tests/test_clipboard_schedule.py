from kookie.clipboard import ClipboardMonitor


def test_clipboard_start_callback_returns_true_for_reschedule() -> None:
    captured = {}

    def scheduler(callback, interval):
        captured["callback"] = callback
        captured["interval"] = interval

        class _Event:
            def cancel(self):
                return None

        return _Event()

    monitor = ClipboardMonitor(read_clipboard=lambda: "", on_new_text=lambda _: None, poll_interval=0.5)
    monitor.start(scheduler)

    assert captured["interval"] == 0.5
    assert captured["callback"](0.5) is True
