from __future__ import annotations

import os
import shutil
import subprocess
import sys
import wave
from collections.abc import Mapping
from pathlib import Path
from typing import Callable

import numpy as np

from .errors import ErrorCategory, ErrorCode, KookieError
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
    quality: int = 2,
) -> Path:
    return save_speech_to_audio(
        backend=backend,
        text=text,
        voice=voice,
        sample_rate=sample_rate,
        output_path=output_path,
        format="mp3",
        normalizer=normalizer,
        chunker=chunker,
        encoder=encoder,
        quality=quality,
    )


def save_speech_to_audio(
    *,
    backend,
    text: str,
    voice: str,
    sample_rate: int,
    output_path: Path,
    format: str = "mp3",
    normalizer: Callable[[str], str] = normalize_text,
    chunker: Callable[[str], list[str]] = split_sentences,
    encoder: Callable[[np.ndarray, int, Path], None] | None = None,
    quality: int = 2,
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
    selected_format = format.strip().lower()
    if selected_format == "mp3":
        selected_encoder = encoder or (lambda audio, sr, path: encode_mp3(audio, sr, path, quality=quality))
        selected_encoder(merged, sample_rate, output)
    elif selected_format == "wav":
        selected_encoder = encoder or encode_wav
        selected_encoder(merged, sample_rate, output)
    else:
        raise ValueError(f"Unsupported export format: {format}")
    return output


def encode_mp3(
    audio: np.ndarray,
    sample_rate: int,
    output_path: Path,
    *,
    quality: int = 2,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    ffmpeg_executable = _resolve_ffmpeg_executable()
    normalized_quality = min(9, max(0, int(quality)))
    command = [
        ffmpeg_executable,
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
        str(normalized_quality),
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
        raise KookieError(
            code=ErrorCode.FILE_NOT_FOUND,
            category=ErrorCategory.FILESYSTEM,
            message="ffmpeg is required to save MP3 files",
            hint="Install ffmpeg and ensure it is available on PATH.",
            detail=str(exc),
        ) from exc

    return_code = int(getattr(result, "returncode", 0))
    if return_code == 0:
        return

    stderr = getattr(result, "stderr", "")
    if isinstance(stderr, bytes):
        detail = stderr.decode("utf-8", errors="ignore").strip()
    else:
        detail = str(stderr).strip()
    if detail:
        raise KookieError(
            code=ErrorCode.BACKEND_FAILURE,
            category=ErrorCategory.BACKEND,
            message=f"MP3 encoding failed: {detail}",
            hint="Retry the export. If it persists, check ffmpeg availability and permissions.",
            detail=detail,
        )
    raise KookieError(
        code=ErrorCode.BACKEND_FAILURE,
        category=ErrorCategory.BACKEND,
        message="MP3 encoding failed",
        hint="Retry the export. If it persists, check ffmpeg availability and permissions.",
    )


def encode_wav(audio: np.ndarray, sample_rate: int, output_path: Path) -> None:
    payload = np.asarray(audio, dtype=np.float32).reshape(-1)
    clipped = np.clip(payload, -1.0, 1.0)
    int16_data = (clipped * 32767.0).astype(np.int16)

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(int16_data.tobytes())


def _resolve_ffmpeg_executable(
    *,
    env: Mapping[str, str] | None = None,
    runtime_base: Path | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> str:
    selected_env = dict(os.environ) if env is None else env
    configured = selected_env.get("KOOKIE_FFMPEG_PATH", "").strip()
    if configured:
        return configured

    base = runtime_base if runtime_base is not None else _runtime_base_path()
    bundled_path = base / "bin" / "ffmpeg"
    if bundled_path.exists():
        return str(bundled_path)

    resolved = which("ffmpeg")
    if resolved:
        return resolved
    return "ffmpeg"


def _runtime_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[arg-type]
    return Path(__file__).resolve().parents[1]
