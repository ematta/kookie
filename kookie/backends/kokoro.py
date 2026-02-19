from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np


class KokoroSpeechBackend:
    name = "kokoro"

    def __init__(self, model_path: str | Path, voices_path: str | Path):
        self.model_path = Path(model_path)
        self.voices_path = Path(voices_path)
        self._configure_espeak_env()
        self._engine = self._create_engine()
        self._voice_cache: list[str] | None = None

    def synthesize_sentences(self, sentences: Iterable[str], voice: str, speed: float = 1.0) -> Iterator[np.ndarray]:
        self.validate_voice(voice)
        bounded_speed = min(2.0, max(0.5, float(speed)))
        for sentence in sentences:
            result = self._engine.create(sentence, voice=voice, speed=bounded_speed, lang="en-us")
            audio = _extract_audio(result)
            yield np.asarray(audio, dtype=np.float32).reshape(-1)

    def list_voices(self) -> list[str]:
        if self._voice_cache is not None:
            return list(self._voice_cache)

        values = getattr(self._engine, "voices", None)
        voices: list[str] = []
        if isinstance(values, dict):
            voices = [str(item).strip() for item in values.keys() if str(item).strip()]
        elif isinstance(values, (list, tuple, set)):
            voices = [str(item).strip() for item in values if str(item).strip()]

        if not voices:
            voices = ["af_sarah"]
        self._voice_cache = sorted(set(voices))
        return list(self._voice_cache)

    def validate_voice(self, voice: str) -> None:
        selected = voice.strip()
        if not selected:
            raise ValueError("Voice name is required.")
        voices = self.list_voices()
        if selected not in voices:
            raise ValueError(f"Unknown voice: {selected}")

    def health_check(self) -> dict[str, object]:
        return {
            "backend": self.name,
            "model_path": str(self.model_path),
            "voices_path": str(self.voices_path),
            "voice_count": len(self.list_voices()),
        }

    def _create_engine(self):
        from kokoro_onnx import Kokoro  # type: ignore

        try:
            return Kokoro(model_path=str(self.model_path), voices_path=str(self.voices_path))
        except TypeError:
            return Kokoro(str(self.model_path), str(self.voices_path))

    def _configure_espeak_env(self) -> None:
        if os.getenv("PHONEMIZER_ESPEAK_LIBRARY") and os.getenv("ESPEAK_DATA_PATH"):
            return

        base = _runtime_base_path()
        candidate_lib = base / "libs" / "libespeak-ng.dylib"
        candidate_data = base / "libs" / "espeak-ng-data"

        if candidate_lib.exists() and not os.getenv("PHONEMIZER_ESPEAK_LIBRARY"):
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = str(candidate_lib)
        if candidate_data.exists() and not os.getenv("ESPEAK_DATA_PATH"):
            os.environ["ESPEAK_DATA_PATH"] = str(candidate_data)


def _runtime_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[arg-type]
    return Path(__file__).resolve().parents[2]


def _extract_audio(result) -> np.ndarray:
    if isinstance(result, np.ndarray):
        return result
    if isinstance(result, (tuple, list)) and result:
        first = result[0]
        if isinstance(first, np.ndarray):
            return first
    return np.asarray(result, dtype=np.float32)
