from __future__ import annotations

import re

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given
from hypothesis import strategies as st

from kookie.text_processing import normalize_text, split_sentences


@given(st.text(min_size=0, max_size=500))
def test_split_sentences_never_exceeds_chunk_limit(value: str) -> None:
    chunks = split_sentences(value, max_chars=120)
    assert all(len(chunk) <= 120 for chunk in chunks)


@given(st.text(min_size=0, max_size=500))
def test_normalize_text_is_idempotent(value: str) -> None:
    normalized = normalize_text(value)
    assert normalize_text(normalized) == normalized
    assert re.search(r"\s{2,}", normalized) is None
