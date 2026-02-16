from __future__ import annotations

import queue
import threading
from typing import Callable

import numpy as np


class AudioPlayer:
    def __init__(self, sample_rate: int = 24_000, stream_factory: Callable[..., object] | None = None):
        self.sample_rate = sample_rate
        self._stream_factory = stream_factory or self._default_stream_factory

    def play_from_queue(self, audio_queue: "queue.Queue[object]", stop_event: threading.Event) -> None:
        with self._stream_factory(sample_rate=self.sample_rate, channels=1, dtype="float32") as stream:
            while True:
                if stop_event.is_set():
                    return

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

                stream.write(data)

    @staticmethod
    def _default_stream_factory(**kwargs):
        import sounddevice as sd  # type: ignore

        return sd.OutputStream(
            samplerate=kwargs["sample_rate"],
            channels=kwargs["channels"],
            dtype=kwargs["dtype"],
        )
