import re

from kookie.text_processing import normalize_text, split_sentences


def test_normalize_text_collapses_whitespace_and_control_chars() -> None:
    raw = "  Hello\t\tworld\n\nfrom\u0000 PDF\u200b copy   "
    assert normalize_text(raw) == "Hello world from PDF copy"


def test_split_sentences_preserves_order_and_punctuation() -> None:
    text = "Hello world! This is a test. Final question?"
    assert split_sentences(text, max_chars=120) == [
        "Hello world!",
        "This is a test.",
        "Final question?",
    ]


def test_split_sentences_chunks_long_segments_deterministically() -> None:
    text = " ".join(["word"] * 40)
    chunks_one = split_sentences(text, max_chars=35)
    chunks_two = split_sentences(text, max_chars=35)

    assert chunks_one == chunks_two
    assert all(len(chunk) <= 35 for chunk in chunks_one)

    rebuilt = re.sub(r"\\s+", " ", " ".join(chunks_one)).strip()
    assert rebuilt == text
