from __future__ import annotations

from functools import lru_cache
import re


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    return _normalize_text_cached(text)


@lru_cache(maxsize=512)
def _normalize_text_cached(text: str) -> str:
    if not text:
        return ""

    cleaned = text.replace("\u00a0", " ").replace("\u200b", "")
    cleaned = "".join(char if (char.isprintable() or char.isspace()) else " " for char in cleaned)
    return _WHITESPACE.sub(" ", cleaned).strip()


def split_sentences(text: str, max_chars: int = 280) -> list[str]:
    return list(_split_sentences_cached(text, max_chars))


@lru_cache(maxsize=512)
def _split_sentences_cached(text: str, max_chars: int = 280) -> tuple[str, ...]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")

    normalized = normalize_text(text)
    if not normalized:
        return ()

    chunks: list[str] = []
    for segment in _SENTENCE_BOUNDARY.split(normalized):
        stripped = segment.strip()
        if not stripped:
            continue
        if len(stripped) <= max_chars:
            chunks.append(stripped)
        else:
            chunks.extend(_chunk_long_segment(stripped, max_chars=max_chars))
    return tuple(chunks)


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


def text_processing_cache_info() -> dict[str, int]:
    normalize_info = _normalize_text_cached.cache_info()
    split_info = _split_sentences_cached.cache_info()
    return {
        "normalize_hits": normalize_info.hits,
        "normalize_misses": normalize_info.misses,
        "normalize_currsize": normalize_info.currsize,
        "split_hits": split_info.hits,
        "split_misses": split_info.misses,
        "split_currsize": split_info.currsize,
    }


def clear_text_processing_cache() -> None:
    _normalize_text_cached.cache_clear()
    _split_sentences_cached.cache_clear()
