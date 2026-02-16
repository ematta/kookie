from __future__ import annotations

from typing import Iterable, Iterator

import numpy as np


class MockSpeechBackend:
    name = "mock"

    def synthesize_sentences(self, sentences: Iterable[str], voice: str) -> Iterator[np.ndarray]:
        del voice
        for sentence in sentences:
            sample_count = max(2_400, len(sentence) * 100)
            timeline = np.linspace(0.0, 0.1, sample_count, endpoint=False, dtype=np.float32)
            waveform = 0.08 * np.sin(2.0 * np.pi * 220.0 * timeline)
            yield waveform.astype(np.float32)
