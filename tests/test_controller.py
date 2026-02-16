import time

import numpy as np

from kookie.controller import PlaybackController, PlaybackState


class _BackendOK:
    def synthesize_sentences(self, sentences, voice):
        for sentence in sentences:
            assert voice == "af_sarah"
            yield np.full(max(4, len(sentence)), 0.1, dtype=np.float32)


class _BackendSlow:
    def synthesize_sentences(self, sentences, voice):
        for sentence in sentences:
            assert voice == "af_sarah"
            time.sleep(0.05)
            yield np.full(max(4, len(sentence)), 0.1, dtype=np.float32)


class _BackendError:
    def synthesize_sentences(self, sentences, voice):
        raise RuntimeError("synthesis exploded")
        yield  # pragma: no cover


class _AudioPlayer:
    def __init__(self):
        self.writes = []

    def play_from_queue(self, audio_queue, stop_event):
        while True:
            chunk = audio_queue.get(timeout=1.0)
            if chunk is None:
                return
            if stop_event.is_set():
                return
            self.writes.append(chunk)


def test_playback_controller_start_stop_idempotency() -> None:
    player = _AudioPlayer()
    controller = PlaybackController(backend=_BackendSlow(), audio_player=player)

    assert controller.start("hello world") is True
    assert controller.start("hello world") is False

    assert controller.stop() is True
    assert controller.stop() is False


def test_playback_controller_processes_queue_and_returns_to_idle() -> None:
    player = _AudioPlayer()
    controller = PlaybackController(backend=_BackendOK(), audio_player=player)

    assert controller.start("one. two.") is True
    controller.wait_until_idle(timeout=2.0)

    assert len(player.writes) >= 2
    assert controller.state is PlaybackState.IDLE


def test_playback_controller_reports_worker_errors() -> None:
    events = []
    controller = PlaybackController(
        backend=_BackendError(),
        audio_player=_AudioPlayer(),
        on_event=events.append,
    )

    assert controller.start("boom") is True

    deadline = time.time() + 2.0
    while time.time() < deadline and controller.state is not PlaybackState.ERROR:
        time.sleep(0.01)

    assert controller.state is PlaybackState.ERROR
    assert controller.last_error is not None
    assert any(event.kind == "error" for event in events)
