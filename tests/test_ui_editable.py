from kookie.ui import _text_input_config


def test_text_input_config_is_editable() -> None:
    cfg = _text_input_config(initial_text="")
    assert cfg["readonly"] is False
    assert cfg["disabled"] is False
    assert cfg["multiline"] is True
    assert cfg["input_type"] == "text"
