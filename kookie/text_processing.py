from __future__ import annotations

import re


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("\u00a0", " ").replace("\u200b", "")
    cleaned = "".join(char if (char.isprintable() or char.isspace()) else " " for char in cleaned)
    return _WHITESPACE.sub(" ", cleaned).strip()


def split_sentences(text: str, max_chars: int = 280) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")

    normalized = normalize_text(text)
    if not normalized:
        return []

    chunks: list[str] = []
    for segment in _SENTENCE_BOUNDARY.split(normalized):
        stripped = segment.strip()
        if not stripped:
            continue
        if len(stripped) <= max_chars:
            chunks.append(stripped)
        else:
            chunks.extend(_chunk_long_segment(stripped, max_chars=max_chars))
    return chunks


def _chunk_long_segment(segment: str, max_chars: int) -> list[str]:
    words = segment.split(" ")
    chunks: list[str] = []
    current = ""

    for word in words:
        if not word:
            continue
        if len(word) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_oversized_word(word, max_chars=max_chars))
            continue

        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = word

    if current:
        chunks.append(current)
    return chunks


def _split_oversized_word(word: str, max_chars: int) -> list[str]:
    return [word[idx : idx + max_chars] for idx in range(0, len(word), max_chars)]
