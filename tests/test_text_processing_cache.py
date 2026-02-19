from __future__ import annotations

from kookie.text_processing import (
    clear_text_processing_cache,
    normalize_text,
    split_sentences,
    text_processing_cache_info,
)


def test_text_processing_cache_records_hits_for_repeated_calls() -> None:
    clear_text_processing_cache()
    text = "This is cached. " * 200

    normalize_text(text)
    split_sentences(text, max_chars=280)
    before = text_processing_cache_info()

    normalize_text(text)
    split_sentences(text, max_chars=280)
    after = text_processing_cache_info()

    assert after["normalize_hits"] > before["normalize_hits"]
    assert after["split_hits"] > before["split_hits"]
