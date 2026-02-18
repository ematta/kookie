from pathlib import Path

import numpy as np
import pytest

from kookie.export import _resolve_ffmpeg_executable, encode_mp3, save_speech_to_mp3


class _Backend:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    def synthesize_sentences(self, sentences, voice):
        materialized = list(sentences)
        self.calls.append((materialized, voice))
        yield np.array([0.1, -0.1], dtype=np.float64)
        yield np.array([[0.2], [0.0]], dtype=np.float32)


def test_save_speech_to_mp3_combines_chunks_and_calls_encoder(tmp_path: Path) -> None:
    backend = _Backend()
    output_path = tmp_path / "speech.mp3"
    capture: dict[str, object] = {}

    def _encoder(audio: np.ndarray, sample_rate: int, output_path: Path) -> None:
        capture["audio"] = audio
        capture["sample_rate"] = sample_rate
        capture["output_path"] = output_path
        output_path.write_bytes(b"mp3")

    saved_path = save_speech_to_mp3(
        backend=backend,
        text="one. two.",
        voice="af_sarah",
        sample_rate=24_000,
        output_path=output_path,
        chunker=lambda _: ["one", "two"],
        encoder=_encoder,
    )

    assert saved_path == output_path
    assert backend.calls == [(["one", "two"], "af_sarah")]
    assert capture["sample_rate"] == 24_000
    assert capture["output_path"] == output_path
    np.testing.assert_allclose(capture["audio"], np.array([0.1, -0.1, 0.2, 0.0], dtype=np.float32))


def test_save_speech_to_mp3_rejects_empty_text(tmp_path: Path) -> None:
    backend = _Backend()

    with pytest.raises(ValueError, match="No text to synthesize"):
        save_speech_to_mp3(
            backend=backend,
            text="   ",
            voice="af_sarah",
            sample_rate=24_000,
            output_path=tmp_path / "speech.mp3",
            normalizer=lambda _: "",
        )


def test_encode_mp3_raises_when_ffmpeg_is_missing(tmp_path: Path) -> None:
    def _runner(*_, **__):
        raise FileNotFoundError("ffmpeg")

    with pytest.raises(RuntimeError, match="ffmpeg is required"):
        encode_mp3(
            audio=np.array([0.1], dtype=np.float32),
            sample_rate=24_000,
            output_path=tmp_path / "speech.mp3",
            runner=_runner,
        )


def test_encode_mp3_raises_when_ffmpeg_fails(tmp_path: Path) -> None:
    class _CompletedProcess:
        returncode = 1
        stderr = "encode failed"

    def _runner(*_, **__):
        return _CompletedProcess()

    with pytest.raises(RuntimeError, match="encode failed"):
        encode_mp3(
            audio=np.array([0.1], dtype=np.float32),
            sample_rate=24_000,
            output_path=tmp_path / "speech.mp3",
            runner=_runner,
        )


def test_resolve_ffmpeg_executable_prefers_env_override(tmp_path: Path) -> None:
    configured = str(tmp_path / "custom-ffmpeg")
    resolved = _resolve_ffmpeg_executable(
        env={"KOOKIE_FFMPEG_PATH": configured},
        runtime_base=tmp_path,
        which=lambda _: None,
    )
    assert resolved == configured


def test_resolve_ffmpeg_executable_uses_bundled_binary_when_available(tmp_path: Path) -> None:
    bundled = tmp_path / "bin" / "ffmpeg"
    bundled.parent.mkdir(parents=True, exist_ok=True)
    bundled.write_text("#!/bin/sh\n", encoding="utf-8")

    resolved = _resolve_ffmpeg_executable(
        env={},
        runtime_base=tmp_path,
        which=lambda _: None,
    )
    assert resolved == str(bundled)


def test_encode_mp3_uses_resolved_ffmpeg_executable(tmp_path: Path, monkeypatch) -> None:
    capture: dict[str, object] = {}

    class _CompletedProcess:
        returncode = 0
        stderr = b""

    def _runner(command, **kwargs):
        capture["command"] = command
        capture["kwargs"] = kwargs
        return _CompletedProcess()

    monkeypatch.setattr("kookie.export._resolve_ffmpeg_executable", lambda: "/tmp/bundled/ffmpeg")

    encode_mp3(
        audio=np.array([0.1, 0.2], dtype=np.float32),
        sample_rate=24_000,
        output_path=tmp_path / "speech.mp3",
        runner=_runner,
    )

    command = capture["command"]
    assert isinstance(command, list)
    assert command[0] == "/tmp/bundled/ffmpeg"
