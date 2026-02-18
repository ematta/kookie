from kookie.ui import (
    STATUS_ACTIVITY_ROW_MIN_HEIGHT,
    STATUS_ACTIVITY_MAX_CHARS,
    STATUS_BAR_HEIGHT,
    STATUS_HEADER_HEIGHT,
    TEXT_FOREGROUND_COLOR,
    _label_text_size_for_width,
    _save_spinner_text,
    _scroll_view_config,
    _status_display_items,
    _status_label_config,
)


def test_text_foreground_color_is_readable_dark_tone() -> None:
    r, g, b, a = TEXT_FOREGROUND_COLOR
    assert 0.0 <= r <= 1.0
    assert 0.0 <= g <= 1.0
    assert 0.0 <= b <= 1.0
    assert a == 1.0
    assert max(r, g, b) < 0.35


def test_scroll_view_config_shows_right_bar_with_wrap_enabled() -> None:
    cfg = _scroll_view_config(word_wrap=True)
    assert cfg["scroll_type"] == ["bars", "content"]
    assert cfg["bar_width"] > 0
    assert cfg["bar_pos_y"] == "right"
    assert cfg["do_scroll_y"] is True
    assert cfg["do_scroll_x"] is False


def test_scroll_view_config_enables_horizontal_scroll_when_wrap_disabled() -> None:
    cfg = _scroll_view_config(word_wrap=False)
    assert cfg["do_scroll_y"] is True
    assert cfg["do_scroll_x"] is True


def test_save_spinner_text_cycles_frames() -> None:
    assert _save_spinner_text(is_saving=True, tick=0) == "Saving MP3 |"
    assert _save_spinner_text(is_saving=True, tick=1) == "Saving MP3 /"
    assert _save_spinner_text(is_saving=True, tick=2) == "Saving MP3 -"
    assert _save_spinner_text(is_saving=True, tick=3) == "Saving MP3 \\"
    assert _save_spinner_text(is_saving=True, tick=4) == "Saving MP3 |"


def test_save_spinner_text_is_empty_when_not_saving() -> None:
    assert _save_spinner_text(is_saving=False, tick=0) == ""
    assert _save_spinner_text(is_saving=False, tick=99) == ""


def test_status_display_items_truncates_long_activity_message() -> None:
    original_items = [
        "Voice: Available",
        "Backend: mock",
        "State: Saved MP3: /Users/ematta/Downloads/very-long-file-name-for-audio-export.mp3",
    ]

    display_items = _status_display_items(original_items)

    assert display_items[0] == original_items[0]
    assert display_items[1] == original_items[1]
    assert len(display_items[2]) <= STATUS_ACTIVITY_MAX_CHARS
    assert display_items[2].startswith("State:")
    assert "..." in display_items[2]


def test_status_label_config_uses_single_line_shortening() -> None:
    cfg = _status_label_config()

    assert cfg["halign"] == "left"
    assert cfg["valign"] == "middle"
    assert cfg["shorten"] is True
    assert cfg["shorten_from"] == "center"
    assert cfg["max_lines"] == 1


def test_status_layout_reserves_enough_vertical_space_for_two_rows() -> None:
    assert STATUS_HEADER_HEIGHT >= 24
    assert STATUS_ACTIVITY_ROW_MIN_HEIGHT >= 24
    assert STATUS_BAR_HEIGHT >= STATUS_HEADER_HEIGHT + STATUS_ACTIVITY_ROW_MIN_HEIGHT


def test_label_text_size_tracks_width_without_forcing_height() -> None:
    assert _label_text_size_for_width(320) == (320, None)
