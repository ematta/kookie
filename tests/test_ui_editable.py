from kookie.editor_prefs import EditorPreferences
from kookie.ui import _text_input_config


def test_text_input_config_is_editable() -> None:
    prefs = EditorPreferences(font_name="Roboto", font_size=20, word_wrap=True)
    cfg = _text_input_config(initial_text="", prefs=prefs)
    assert cfg["readonly"] is False
    assert cfg["font_family"] == "Roboto"
    assert cfg["font_size"] == 20
    assert cfg["word_wrap"] is True
    assert cfg["accept_tab"] is True
    assert cfg["text"] == ""
    assert "foreground_color" in cfg
    assert "background_color" in cfg
    assert "selection_color" in cfg
    assert "cursor_color" in cfg
    assert cfg["padding"] == [16, 16, 16, 16]
