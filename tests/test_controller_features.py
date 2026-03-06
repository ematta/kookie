from __future__ import annotations

import threading
import time

import numpy as np
from conftest import _AudioPlayer

from kookie.controller import PlaybackController, PlaybackState


class _BackendSlow:
    def synthesize_sentences(self, sentences, voice):
        del voice
        for sentence in sentences:
            time.sleep(0.02)
            yield np.full(max(4, len(sentence)), 0.25, dtype=np.float32)


def test_playback_controller_pause_and_resume() -> None:
    playing_event = threading.Event()

    def on_event(e):
        if e.state in {PlaybackState.PLAYING, PlaybackState.PAUSED}:
            playing_event.set()

    controller = PlaybackController(backend=_BackendSlow(), audio_player=_AudioPlayer(), on_event=on_event)
    assert controller.start("one. two. three.") is True

    playing_event.wait(timeout=2.0)

    assert controller.pause() is True
    assert controller.state is PlaybackState.PAUSED
    assert controller.resume() is True
    assert controller.state in {PlaybackState.PLAYING, PlaybackState.SYNTHESIZING}

    controller.stop()
    controller.wait_until_idle(timeout=2.0)


def test_playback_controller_volume_seek_and_progress() -> None:
    controller = PlaybackController(backend=_BackendSlow(), audio_player=_AudioPlayer())
    assert controller.set_volume(1.5) == 1.0
    assert controller.set_volume(-1.0) == 0.0
    assert controller.set_volume(0.5) == 0.5

    assert controller.start("one. two. three. four.") is True
    assert controller.seek(seconds=0.1) is True
    controller.wait_until_idle(timeout=2.0)

    progress = controller.progress
    assert progress["played_samples"] >= 0
    assert progress["synthesized_samples"] >= progress["played_samples"]
