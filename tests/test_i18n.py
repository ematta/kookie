from __future__ import annotations

from kookie.i18n import get_translator


def test_get_translator_defaults_to_english() -> None:
    tr = get_translator("en")
    assert tr("Play") == "Play"


def test_get_translator_supports_spanish() -> None:
    tr = get_translator("es")
    assert tr("Play") == "Reproducir"
    assert tr("Save MP3") == "Guardar MP3"


def test_get_translator_falls_back_for_unknown_language() -> None:
    tr = get_translator("fr")
    assert tr("Stop") == "Stop"
