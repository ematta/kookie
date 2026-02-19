from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Protocol

import numpy as np


class SpeechBackend(Protocol):
    def synthesize_sentences(
        self,
        sentences: Iterable[str],
        voice: str,
        speed: float = 1.0,
    ) -> Iterator[np.ndarray]:
        """Yield float32 audio chunks for each sentence."""
