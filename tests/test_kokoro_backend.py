from __future__ import annotations

from types import SimpleNamespace

import pytest

from kookie.backends.kokoro import KokoroSpeechBackend


def test_kokoro_backend_can_enumerate_voices_from_engine_cache() -> None:
    backend = object.__new__(KokoroSpeechBackend)
    backend._engine = SimpleNamespace(voices={"af_sarah": {}, "af_nicole": {}})
    backend._voice_cache = None

    voices = backend.list_voices()

    assert voices == ["af_nicole", "af_sarah"]


def test_kokoro_backend_validate_voice_rejects_unknown_voice() -> None:
    backend = object.__new__(KokoroSpeechBackend)
    backend._engine = SimpleNamespace(voices={"af_sarah": {}})
    backend._voice_cache = None

    with pytest.raises(ValueError, match="Unknown voice"):
        backend.validate_voice("invalid_voice")
