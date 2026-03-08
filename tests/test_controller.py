import threading
import time

import numpy as np
from conftest import _AudioPlayer

from kookie.controller import PlaybackController, PlaybackState


class _BackendOK:
    def __init__(self) -> None:
        self.received_voice: str | None = None

    def synthesize_sentences(self, sentences, voice):
        self.received_voice = voice
        for sentence in sentences:
            yield np.full(max(4, len(sentence)), 0.1, dtype=np.float32)


class _BackendSlow:
    def __init__(self) -> None:
        self.received_voice: str | None = None

    def synthesize_sentences(self, sentences, voice):
        self.received_voice = voice
        for sentence in sentences:
            time.sleep(0.05)
            yield np.full(max(4, len(sentence)), 0.1, dtype=np.float32)


class _BackendError:
    def synthesize_sentences(self, sentences, voice):
        raise RuntimeError("synthesis exploded")
        yield  # pragma: no cover


def test_playback_controller_start_stop_idempotency() -> None:
    player = _AudioPlayer()
    controller = PlaybackController(backend=_BackendSlow(), audio_player=player)

    assert controller.start("hello world") is True
    assert controller.start("hello world") is False

    assert controller.stop() is True
    assert controller.stop() is False


def test_playback_controller_processes_queue_and_returns_to_idle() -> None:
    player = _AudioPlayer()
    backend = _BackendOK()
    controller = PlaybackController(backend=backend, audio_player=player)

    assert controller.start("one. two.") is True
    controller.wait_until_idle(timeout=2.0)

    assert len(player.writes) >= 2
    assert controller.state is PlaybackState.IDLE
    assert backend.received_voice == "af_sarah"


def test_playback_controller_reports_worker_errors() -> None:
    events = []
    error_event = threading.Event()

    def on_event(e):
        events.append(e)
        if e.kind == "error":
            error_event.set()

    controller = PlaybackController(
        backend=_BackendError(),
        audio_player=_AudioPlayer(),
        on_event=on_event,
    )

    assert controller.start("boom") is True

    error_event.wait(timeout=2.0)

    assert controller.state is PlaybackState.ERROR
    assert controller.last_error is not None
    assert any(event.kind == "error" for event in events)


def test_pause_when_idle_returns_false() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.pause() is False


def test_resume_when_not_paused_returns_false() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.resume() is False


def test_seek_negative_seconds_returns_false() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.seek(seconds=-1) is False


def test_seek_zero_seconds_returns_false() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.seek(seconds=0) is False


def test_seek_when_idle_returns_false() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.seek(seconds=1.0) is False


def test_set_playback_speed_clamps_below_minimum() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.set_playback_speed(0.0) == 0.5


def test_set_playback_speed_clamps_above_maximum() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.set_playback_speed(5.0) == 2.0


def test_set_volume_clamps_below_zero() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.set_volume(-1.0) == 0.0


def test_set_volume_clamps_above_one() -> None:
    controller = PlaybackController(backend=_BackendOK(), audio_player=_AudioPlayer())
    assert controller.set_volume(2.0) == 1.0
