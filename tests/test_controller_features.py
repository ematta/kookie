from __future__ import annotations

import time

import numpy as np

from kookie.controller import PlaybackController, PlaybackState


class _BackendSlow:
    def synthesize_sentences(self, sentences, voice):
        del voice
        for sentence in sentences:
            time.sleep(0.02)
            yield np.full(max(4, len(sentence)), 0.25, dtype=np.float32)


class _AudioPlayer:
    def play_from_queue(
        self,
        audio_queue,
        stop_event,
        pause_event=None,
        volume_getter=None,
        on_progress=None,
        consume_seek_samples=None,
    ):
        pending_seek = 0
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
                pending_seek += max(0, int(consume_seek_samples()))
            data = np.asarray(chunk, dtype=np.float32).reshape(-1)
            if pending_seek > 0:
                if data.size <= pending_seek:
                    pending_seek -= data.size
                    continue
                data = data[pending_seek:]
                pending_seek = 0
            if volume_getter is not None:
                data = data * float(volume_getter())
            if on_progress is not None:
                on_progress(int(data.size))


def test_playback_controller_pause_and_resume() -> None:
    controller = PlaybackController(backend=_BackendSlow(), audio_player=_AudioPlayer())
    assert controller.start("one. two. three.") is True

    deadline = time.time() + 2.0
    while time.time() < deadline and controller.state not in {PlaybackState.PLAYING, PlaybackState.PAUSED}:
        time.sleep(0.01)

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
