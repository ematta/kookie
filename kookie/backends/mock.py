from __future__ import annotations

from collections.abc import Iterable, Iterator

import numpy as np


class MockSpeechBackend:
    name = "mock"

    def __init__(
        self,
        *,
        frequency_hz: float = 220.0,
        amplitude: float = 0.08,
        mode: str = "sine",
    ):
        self.frequency_hz = max(20.0, float(frequency_hz))
        self.amplitude = min(1.0, max(0.0, float(amplitude)))
        self.mode = mode.strip().lower() if isinstance(mode, str) else "sine"

    def synthesize_sentences(
        self,
        sentences: Iterable[str],
        voice: str,
        speed: float = 1.0,
    ) -> Iterator[np.ndarray]:
        del voice
        bounded_speed = min(2.0, max(0.5, float(speed)))
        duration = max(0.04, 0.1 / bounded_speed)
        for sentence in sentences:
            sample_count = max(2_400, len(sentence) * 100)
            timeline = np.linspace(0.0, duration, sample_count, endpoint=False, dtype=np.float32)
            waveform = self._waveform(timeline)
            yield waveform.astype(np.float32)

    def _waveform(self, timeline: np.ndarray) -> np.ndarray:
        radians = 2.0 * np.pi * self.frequency_hz * timeline
        if self.mode == "square":
            return self.amplitude * np.sign(np.sin(radians))
        if self.mode == "saw":
            return self.amplitude * (2.0 * ((self.frequency_hz * timeline) % 1.0) - 1.0)
        return self.amplitude * np.sin(radians)
