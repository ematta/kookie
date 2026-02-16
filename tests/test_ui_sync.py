from kookie.ui import _next_text_value


def test_next_text_value_preserves_user_text_without_clipboard_update() -> None:
    assert (
        _next_text_value(
            current_text="typed text",
            clipboard_text=None,
            is_focused=True,
            auto_clipboard_sync=False,
        )
        == "typed text"
    )


def test_next_text_value_applies_clipboard_update_when_enabled() -> None:
    assert (
        _next_text_value(
            current_text="typed text",
            clipboard_text="clipboard text",
            is_focused=False,
            auto_clipboard_sync=True,
        )
        == "clipboard text"
    )


def test_next_text_value_does_not_override_focused_editor() -> None:
    assert (
        _next_text_value(
            current_text="typed text",
            clipboard_text="clipboard text",
            is_focused=True,
            auto_clipboard_sync=True,
        )
        == "typed text"
    )


def test_next_text_value_ignores_clipboard_when_auto_sync_disabled() -> None:
    assert (
        _next_text_value(
            current_text="typed text",
            clipboard_text="clipboard text",
            is_focused=False,
            auto_clipboard_sync=False,
        )
        == "typed text"
    )
