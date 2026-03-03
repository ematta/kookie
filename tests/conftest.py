from __future__ import annotations

import time

import numpy as np
import pytest

_NON_UNIT_MARKERS = {"integration", "e2e", "perf"}


class _AudioPlayer:
    """Canonical test double for AudioPlayer.

    Supports the full play_from_queue signature used by PlaybackController,
    including optional pause, volume, progress, and seek-sample parameters.
    Chunks are recorded in ``self.writes`` for inspection in tests.
    """

    sample_rate = 24_000

    def __init__(self) -> None:
        self.writes: list = []

    def play_from_queue(
        self,
        audio_queue,
        stop_event,
        pause_event=None,
        volume_getter=None,
        on_progress=None,
        consume_seek_samples=None,
    ) -> None:
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
            self.writes.append(chunk)
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


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        marker_names = {marker.name for marker in item.iter_markers()}
        if marker_names.isdisjoint(_NON_UNIT_MARKERS):
            item.add_marker(pytest.mark.unit)
