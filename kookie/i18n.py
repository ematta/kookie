from __future__ import annotations

import gettext
from collections.abc import Callable
from functools import lru_cache

_ES_TRANSLATIONS = {
    "Load PDF": "Cargar PDF",
    "Play": "Reproducir",
    "Stop": "Detener",
    "Save MP3": "Guardar MP3",
    "Saving MP3": "Guardando MP3",
    "Ready": "Listo",
}


class _DictTranslations(gettext.NullTranslations):
    def __init__(self, mapping: dict[str, str]):
        super().__init__()
        self._mapping = mapping

    def gettext(self, message: str) -> str:
        return self._mapping.get(message, message)


@lru_cache(maxsize=8)
def _translation_for(language: str) -> gettext.NullTranslations:
    selected = (language or "en").strip().lower()
    if selected == "es":
        return _DictTranslations(_ES_TRANSLATIONS)
    return gettext.NullTranslations()


def get_translator(language: str | None) -> Callable[[str], str]:
    translation = _translation_for((language or "en").strip().lower())
    return translation.gettext
