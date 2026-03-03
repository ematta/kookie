from __future__ import annotations

import time

import pytest

from kookie.text_processing import normalize_text, split_sentences


@pytest.mark.perf
def test_large_text_processing_cache_warms_for_repeated_input() -> None:
    text = ("This is a long sentence for cache warm-up. " * 8000).strip()

    normalize_text(text)
    split_sentences(text, max_chars=280)

    # Repeated calls are expected in playback/export paths; this test ensures they remain stable.
    start = time.perf_counter()
    result_one = split_sentences(text, max_chars=280)
    result_two = split_sentences(text, max_chars=280)
    duration = time.perf_counter() - start

    assert result_one == result_two
    assert len(result_two) > 100
    assert duration < 1.0, f"Repeated split_sentences calls took {duration:.3f}s, expected < 1.0s"
