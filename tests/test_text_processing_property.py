from __future__ import annotations

import re

import pytest

from kookie.text_processing import normalize_text, split_sentences

hypothesis = pytest.importorskip("hypothesis")
given = hypothesis.given
st = hypothesis.strategies


@given(st.text(min_size=0, max_size=500))
def test_split_sentences_never_exceeds_chunk_limit(value: str) -> None:
    chunks = split_sentences(value, max_chars=120)
    assert all(len(chunk) <= 120 for chunk in chunks)


@given(st.text(min_size=0, max_size=500))
def test_normalize_text_is_idempotent(value: str) -> None:
    normalized = normalize_text(value)
    assert normalize_text(normalized) == normalized
    assert re.search(r"\s{2,}", normalized) is None


@given(st.text(min_size=0, max_size=500))
def test_split_sentences_produces_no_empty_chunks(value: str) -> None:
    chunks = split_sentences(value, max_chars=120)
    assert all(len(chunk) > 0 for chunk in chunks)


@given(st.text(min_size=0, max_size=500))
def test_split_sentences_preserves_all_content(value: str) -> None:
    chunks = split_sentences(value, max_chars=120)
    assert " ".join(chunks) == normalize_text(value)


@given(st.text(min_size=0, max_size=500), st.integers(min_value=1, max_value=500))
def test_split_sentences_max_chars_holds_for_any_limit(value: str, max_chars: int) -> None:
    chunks = split_sentences(value, max_chars=max_chars)
    assert all(len(chunk) <= max_chars for chunk in chunks)
