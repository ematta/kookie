from __future__ import annotations

import numpy as np

from kookie.backends.mock import MockSpeechBackend


def test_mock_backend_supports_configurable_frequency() -> None:
    backend = MockSpeechBackend(frequency_hz=440.0)
    chunks = list(backend.synthesize_sentences(["hello"], voice="af_sarah", speed=1.0))

    assert len(chunks) == 1
    assert chunks[0].dtype == np.float32
    assert chunks[0].size >= 2400


def test_mock_backend_supports_square_wave_mode() -> None:
    backend = MockSpeechBackend(mode="square")
    chunk = list(backend.synthesize_sentences(["hello"], voice="af_sarah"))[0]

    unique_values = np.unique(np.round(chunk, decimals=2))
    assert len(unique_values) <= 4
