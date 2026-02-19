from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable

import numpy as np


class AudioPlayer:
    def __init__(self, sample_rate: int = 24_000, stream_factory: Callable[..., object] | None = None):
        self.sample_rate = sample_rate
        self._stream_factory = stream_factory or self._default_stream_factory

    def play_from_queue(
        self,
        audio_queue: queue.Queue[object],
        stop_event: threading.Event,
        pause_event: threading.Event | None = None,
        volume_getter: Callable[[], float] | None = None,
        on_progress: Callable[[int], None] | None = None,
        consume_seek_samples: Callable[[], int] | None = None,
    ) -> None:
        pending_seek_samples = 0
        with self._stream_factory(sample_rate=self.sample_rate, channels=1, dtype="float32") as stream:
            while True:
                if stop_event.is_set():
                    return
                if pause_event is not None and pause_event.is_set():
                    time.sleep(0.01)
                    continue

                try:
                    chunk = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if chunk is None:
                    return
                if stop_event.is_set():
                    return

                data = np.asarray(chunk, dtype=np.float32).reshape(-1)
                if data.size == 0:
                    continue

                if consume_seek_samples is not None:
                    pending_seek_samples += max(0, int(consume_seek_samples()))

                if pending_seek_samples > 0:
                    if data.size <= pending_seek_samples:
                        pending_seek_samples -= data.size
                        continue
                    data = data[pending_seek_samples:]
                    pending_seek_samples = 0

                if volume_getter is not None:
                    volume = float(volume_getter())
                    volume = min(1.0, max(0.0, volume))
                    data = data * volume

                stream.write(data)
                if on_progress is not None:
                    on_progress(int(data.size))

    @staticmethod
    def _default_stream_factory(**kwargs):
        import sounddevice as sd  # type: ignore

        return sd.OutputStream(
            samplerate=kwargs["sample_rate"],
            channels=kwargs["channels"],
            dtype=kwargs["dtype"],
        )
