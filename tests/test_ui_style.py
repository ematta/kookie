from kookie.ui import TEXT_FOREGROUND_COLOR, _save_spinner_text, _scroll_view_config


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
