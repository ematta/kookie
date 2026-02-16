import queue
import threading

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


def test_audio_player_streams_until_sentinel() -> None:
    stream = _FakeStream()
    player = AudioPlayer(sample_rate=24000, stream_factory=lambda **_: stream)
    audio_queue = queue.Queue()
    audio_queue.put(np.array([0.1, -0.1], dtype=np.float32))
    audio_queue.put(None)

    player.play_from_queue(audio_queue, stop_event=threading.Event())

    assert len(stream.writes) == 1
    assert stream.writes[0].shape[0] == 2


def test_audio_player_respects_stop_event() -> None:
    stream = _FakeStream()
    player = AudioPlayer(sample_rate=24000, stream_factory=lambda **_: stream)
    audio_queue = queue.Queue()
    audio_queue.put(np.array([0.5], dtype=np.float32))
    audio_queue.put(None)

    stop_event = threading.Event()
    stop_event.set()

    player.play_from_queue(audio_queue, stop_event=stop_event)

    assert stream.writes == []
