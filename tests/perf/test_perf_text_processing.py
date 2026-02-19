from __future__ import annotations

import pytest

from kookie.text_processing import normalize_text, split_sentences


@pytest.mark.perf
def test_large_text_processing_cache_warms_for_repeated_input() -> None:
    text = ("This is a long sentence for cache warm-up. " * 8000).strip()

    normalize_text(text)
    split_sentences(text, max_chars=280)

    # Repeated calls are expected in playback/export paths; this test ensures they remain stable.
    result_one = split_sentences(text, max_chars=280)
    result_two = split_sentences(text, max_chars=280)

    assert result_one == result_two
    assert len(result_two) > 100
