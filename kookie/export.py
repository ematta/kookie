from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

import numpy as np

from .text_processing import normalize_text, split_sentences


def save_speech_to_mp3(
    *,
    backend,
    text: str,
    voice: str,
    sample_rate: int,
    output_path: Path,
    normalizer: Callable[[str], str] = normalize_text,
    chunker: Callable[[str], list[str]] = split_sentences,
    encoder: Callable[[np.ndarray, int, Path], None] | None = None,
) -> Path:
    normalized = normalizer(text)
    if not normalized:
        raise ValueError("No text to synthesize")

    sentences = chunker(normalized)
    if not sentences:
        raise ValueError("No text to synthesize")

    chunks: list[np.ndarray] = []
    for chunk in backend.synthesize_sentences(sentences, voice):
        data = np.asarray(chunk, dtype=np.float32).reshape(-1)
        if data.size > 0:
            chunks.append(data)

    if not chunks:
        raise ValueError("No synthesized audio to save")

    output = output_path.expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)

    merged = np.concatenate(chunks).astype(np.float32, copy=False)
    selected_encoder = encoder or encode_mp3
    selected_encoder(merged, sample_rate, output)
    return output


def encode_mp3(
    audio: np.ndarray,
    sample_rate: int,
    output_path: Path,
    *,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "f32le",
        "-ar",
        str(sample_rate),
        "-ac",
        "1",
        "-i",
        "pipe:0",
        "-vn",
        "-q:a",
        "2",
        str(output_path),
    ]

    payload = np.asarray(audio, dtype=np.float32).reshape(-1).tobytes()

    try:
        result = runner(
            command,
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required to save MP3 files") from exc

    return_code = int(getattr(result, "returncode", 0))
    if return_code == 0:
        return

    stderr = getattr(result, "stderr", "")
    if isinstance(stderr, bytes):
        detail = stderr.decode("utf-8", errors="ignore").strip()
    else:
        detail = str(stderr).strip()
    if detail:
        raise RuntimeError(f"MP3 encoding failed: {detail}")
    raise RuntimeError("MP3 encoding failed")
