from __future__ import annotations

from typing import Iterable, Iterator, Protocol

import numpy as np


class SpeechBackend(Protocol):
    def synthesize_sentences(
        self,
        sentences: Iterable[str],
        voice: str,
        speed: float = 1.0,
    ) -> Iterator[np.ndarray]:
        """Yield float32 audio chunks for each sentence."""
