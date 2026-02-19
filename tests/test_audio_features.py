from __future__ import annotations

import queue
import threading
import time

import numpy as np

from kookie.audio import AudioPlayer


class _FakeStream:
    def __init__(self):
        self.writes = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def write(self, data):
        self.writes.append(np.asarray(data).copy())


def test_audio_player_applies_volume_scaling() -> None:
    stream = _FakeStream()
    player = AudioPlayer(sample_rate=24_000, stream_factory=lambda **_: stream)
    audio_queue = queue.Queue()
    audio_queue.put(np.array([1.0, -1.0], dtype=np.float32))
    audio_queue.put(None)

    player.play_from_queue(
        audio_queue,
        stop_event=threading.Event(),
        volume_getter=lambda: 0.5,
    )

    assert len(stream.writes) == 1
    np.testing.assert_allclose(stream.writes[0], np.array([0.5, -0.5], dtype=np.float32))


def test_audio_player_supports_seek_by_skipping_samples() -> None:
    stream = _FakeStream()
    player = AudioPlayer(sample_rate=24_000, stream_factory=lambda **_: stream)
    audio_queue = queue.Queue()
    audio_queue.put(np.array([0.1, 0.2, 0.3], dtype=np.float32))
    audio_queue.put(None)
    seek_values = [2, 0]

    def _consume_seek() -> int:
        return seek_values.pop(0) if seek_values else 0

    player.play_from_queue(
        audio_queue,
        stop_event=threading.Event(),
        consume_seek_samples=_consume_seek,
    )

    assert len(stream.writes) == 1
    np.testing.assert_allclose(stream.writes[0], np.array([0.3], dtype=np.float32))


def test_audio_player_waits_while_paused() -> None:
    stream = _FakeStream()
    player = AudioPlayer(sample_rate=24_000, stream_factory=lambda **_: stream)
    audio_queue = queue.Queue()
    stop_event = threading.Event()
    pause_event = threading.Event()
    pause_event.set()
    audio_queue.put(np.array([0.2, 0.4], dtype=np.float32))
    audio_queue.put(None)

    worker = threading.Thread(
        target=player.play_from_queue,
        kwargs={
            "audio_queue": audio_queue,
            "stop_event": stop_event,
            "pause_event": pause_event,
        },
        daemon=True,
    )
    worker.start()
    time.sleep(0.05)
    assert stream.writes == []

    pause_event.clear()
    worker.join(timeout=1.0)
    assert len(stream.writes) == 1
