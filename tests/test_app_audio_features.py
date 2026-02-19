from __future__ import annotations

import time
from pathlib import Path

from kookie.app import create_app
from kookie.config import AppConfig
from kookie.controller import PlaybackState


class _AudioPlayer:
    sample_rate = 24_000

    def play_from_queue(
        self,
        audio_queue,
        stop_event,
        pause_event=None,
        volume_getter=None,
        on_progress=None,
        consume_seek_samples=None,
    ):
        while True:
            if stop_event.is_set():
                return
            if pause_event is not None and pause_event.is_set():
                time.sleep(0.005)
                continue
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if consume_seek_samples is not None:
                consume_seek_samples()
            if on_progress is not None:
                on_progress(len(chunk))


def test_runtime_exposes_volume_speed_and_progress_controls(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    assert runtime.set_volume(2.0) == 1.0
    assert runtime.set_volume(-1.0) == 0.0
    assert runtime.set_volume(0.5) == 0.5
    assert runtime.set_playback_speed(3.0) == 2.0
    assert runtime.set_playback_speed(0.1) == 0.5

    runtime.set_text("One sentence. Two sentence.")
    assert runtime.play() is True
    runtime.wait_until_idle(timeout=2.0)

    progress = runtime.playback_progress
    assert progress["played_samples"] >= 0
    assert progress["synthesized_samples"] >= progress["played_samples"]


def test_runtime_pause_resume_and_seek(tmp_path: Path) -> None:
    runtime = create_app(
        AppConfig(backend_mode="mock", asset_dir=tmp_path),
        ensure_download=False,
        audio_player=_AudioPlayer(),
    )

    runtime.set_text("One sentence. Two sentence. Three sentence.")
    assert runtime.play() is True

    deadline = time.time() + 2.0
    while time.time() < deadline and runtime.controller.state not in {PlaybackState.PLAYING, PlaybackState.PAUSED}:
        time.sleep(0.01)

    paused = runtime.pause()
    if paused:
        assert runtime.resume() is True
        assert runtime.seek(seconds=0.1) is True
    else:
        assert runtime.controller.state is PlaybackState.IDLE
    runtime.stop()
    runtime.wait_until_idle(timeout=2.0)
