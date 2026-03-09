from kookie.ui import (
    CONTROL_FONT_SIZE,
    STATUS_ACTIVITY_MAX_CHARS,
    STATUS_ACTIVITY_ROW_MIN_HEIGHT,
    STATUS_BAR_HEIGHT,
    STATUS_BAR_PADDING,
    STATUS_BAR_ROW_SPACING,
    STATUS_FONT_SIZE,
    STATUS_HEADER_HEIGHT,
    STATUS_PROGRESS_ROW_MIN_HEIGHT,
    STATUS_RECENT_ROW_MIN_HEIGHT,
    TEXT_FOREGROUND_COLOR,
    _app_icon_path,
    _label_text_size_for_width,
    _save_spinner_text,
    _status_display_items,
    _update_recent_files,
    detect_system_dark_mode,
)


def test_text_foreground_color_is_readable_dark_tone() -> None:
    r, g, b, a = TEXT_FOREGROUND_COLOR
    assert 0.0 <= r <= 1.0
    assert 0.0 <= g <= 1.0
    assert 0.0 <= b <= 1.0
    assert a == 1.0
    assert max(r, g, b) < 0.35



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



def test_status_layout_reserves_enough_vertical_space_for_all_rows() -> None:
    status_vertical_padding = STATUS_BAR_PADDING[1] + STATUS_BAR_PADDING[3]

    minimum_content_height = (
        STATUS_HEADER_HEIGHT
        + STATUS_ACTIVITY_ROW_MIN_HEIGHT
        + STATUS_PROGRESS_ROW_MIN_HEIGHT
        + STATUS_RECENT_ROW_MIN_HEIGHT
        + (STATUS_BAR_ROW_SPACING * 3)
        + status_vertical_padding
    )

    assert STATUS_HEADER_HEIGHT >= 34
    assert STATUS_ACTIVITY_ROW_MIN_HEIGHT >= 34
    assert STATUS_BAR_HEIGHT >= minimum_content_height


def test_label_text_size_tracks_width_without_forcing_height() -> None:
    assert _label_text_size_for_width(320) == (320, None)


def test_update_recent_files_deduplicates_and_caps_list() -> None:
    files = ["/tmp/a.pdf", "/tmp/b.pdf", "/tmp/c.pdf"]
    updated = _update_recent_files(files, "/tmp/b.pdf", max_items=3)

    assert updated == ["/tmp/b.pdf", "/tmp/a.pdf", "/tmp/c.pdf"]

    updated = _update_recent_files(updated, "/tmp/d.pdf", max_items=3)
    assert updated == ["/tmp/d.pdf", "/tmp/b.pdf", "/tmp/a.pdf"]


def test_detect_system_dark_mode_parses_apple_script_output() -> None:
    def _runner(*_args, **_kwargs):
        class _Completed:
            stdout = "true\n"
        return _Completed()

    assert detect_system_dark_mode(platform_name="darwin", runner=_runner) is True


def test_app_icon_path_returns_png_path_when_present(tmp_path) -> None:
    icon_path = tmp_path / "kookie.png"
    icon_path.write_bytes(b"png")

    assert _app_icon_path(runtime_base=tmp_path) == str(icon_path)


def test_app_icon_path_returns_none_when_png_missing(tmp_path) -> None:
    assert _app_icon_path(runtime_base=tmp_path) is None


def test_control_font_size_is_at_least_20() -> None:
    size = int(str(CONTROL_FONT_SIZE).replace("sp", ""))
    assert size >= 20


def test_status_font_size_is_readable() -> None:
    size = int(str(STATUS_FONT_SIZE).replace("sp", ""))
    assert size >= 16


def test_font_sizes_use_sp_units_for_retina_scaling() -> None:
    from kookie.ui import URL_INPUT_FONT_SIZE

    assert str(CONTROL_FONT_SIZE).endswith("sp"), "CONTROL_FONT_SIZE must use sp units for Retina scaling"
    assert str(STATUS_FONT_SIZE).endswith("sp"), "STATUS_FONT_SIZE must use sp units for Retina scaling"
    assert str(URL_INPUT_FONT_SIZE).endswith("sp"), "URL_INPUT_FONT_SIZE must use sp units for Retina scaling"
