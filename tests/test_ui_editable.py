from kookie.editor_prefs import EditorPreferences
from kookie.ui import _text_input_config


def test_text_input_config_is_editable() -> None:
    prefs = EditorPreferences(font_name="Roboto", font_size=20, word_wrap=True)
    cfg = _text_input_config(initial_text="", prefs=prefs)
    assert cfg["readonly"] is False
    assert cfg["disabled"] is False
    assert cfg["multiline"] is True
    assert cfg["input_type"] == "text"
    assert cfg["font_name"] == "Roboto"
    assert cfg["font_size"] == 20
    assert cfg["do_wrap"] is True
    assert cfg["write_tab"] is True
    assert cfg["background_normal"] == ""
    assert cfg["background_active"] == ""
    assert "background_disabled_active" not in cfg
