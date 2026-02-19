from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

from .text_processing import normalize_text, split_sentences


class PlaybackState(Enum):
    IDLE = "idle"
    SYNTHESIZING = "synthesizing"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(slots=True)
class ControllerEvent:
    kind: str
    state: PlaybackState
    message: str = ""


class PlaybackController:
    def __init__(
        self,
        backend,
        audio_player,
        *,
        on_event: Callable[[ControllerEvent], None] | None = None,
        normalizer: Callable[[str], str] = normalize_text,
        chunker: Callable[[str], list[str]] = split_sentences,
        queue_timeout: float = 0.1,
        queue_maxsize: int = 8,
    ):
        self.backend = backend
        self.audio_player = audio_player
        self._on_event = on_event
        self._normalizer = normalizer
        self._chunker = chunker
        self._queue_timeout = max(0.01, queue_timeout)
        self._queue_maxsize = max(1, queue_maxsize)

        self._lock = threading.Lock()
        self._state = PlaybackState.IDLE
        self._audio_queue: queue.Queue[object] | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kookie")
        self._synthesis_future: Future[None] | None = None
        self._audio_future: Future[None] | None = None
        self._volume = 1.0
        self._seek_samples = 0
        self._synthesized_samples = 0
        self._played_samples = 0
        self._playback_speed = 1.0
        self._sample_rate = int(getattr(audio_player, "sample_rate", 24_000))
        self.last_error: Exception | None = None

    @property
    def state(self) -> PlaybackState:
        with self._lock:
            return self._state

    @property
    def progress(self) -> dict[str, int]:
        with self._lock:
            return {
                "played_samples": self._played_samples,
                "synthesized_samples": self._synthesized_samples,
            }

    @property
    def volume(self) -> float:
        with self._lock:
            return self._volume

    def start(self, text: str, voice: str = "af_sarah") -> bool:
        normalized = self._normalizer(text)
        if not normalized:
            return False

        with self._lock:
            if self._is_running_locked():
                return False

            sentences = self._chunker(normalized)
            if not sentences:
                return False

            self.last_error = None
            self._audio_queue = queue.Queue(maxsize=self._queue_maxsize)
            self._stop_event = threading.Event()
            self._pause_event = threading.Event()
            self._seek_samples = 0
            self._synthesized_samples = 0
            self._played_samples = 0
            self._state = PlaybackState.SYNTHESIZING
            self._synthesis_future = self._executor.submit(self._run_synthesis, sentences, voice)
            self._audio_future = self._executor.submit(self._run_audio)

        self._emit("state", PlaybackState.SYNTHESIZING)
        return True

    def stop(self) -> bool:
        with self._lock:
            running = self._is_running_locked()
            if not running and self._audio_queue is None:
                return False
            if self._stop_event.is_set():
                return False

            self._stop_event.set()
            self._pause_event.clear()
            self._state = PlaybackState.STOPPING if running else PlaybackState.IDLE
            audio_queue = self._audio_queue

        if audio_queue is not None:
            try:
                audio_queue.put_nowait(None)
            except queue.Full:
                pass

        self._emit("state", PlaybackState.STOPPING)
        return True

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            current_state = self.state
            if current_state in {PlaybackState.IDLE, PlaybackState.ERROR} and not self._is_running():
                return
            time.sleep(0.01)

        self.stop()
        self._join_futures(timeout=0.05)

    def pause(self) -> bool:
        with self._lock:
            if not self._is_running_locked() or self._state is PlaybackState.ERROR:
                return False
            if self._pause_event.is_set():
                return False
            self._pause_event.set()
            self._state = PlaybackState.PAUSED
        self._emit("state", PlaybackState.PAUSED)
        return True

    def resume(self) -> bool:
        with self._lock:
            if not self._pause_event.is_set():
                return False
            self._pause_event.clear()
            if self._state is not PlaybackState.ERROR:
                self._state = PlaybackState.PLAYING
        self._emit("state", PlaybackState.PLAYING)
        return True

    def set_volume(self, volume: float) -> float:
        bounded = min(1.0, max(0.0, float(volume)))
        with self._lock:
            self._volume = bounded
        return bounded

    def seek(self, *, seconds: float) -> bool:
        if seconds <= 0:
            return False
        with self._lock:
            if not self._is_running_locked():
                return False
            self._seek_samples += int(seconds * self._sample_rate)
            return True

    def set_playback_speed(self, speed: float) -> float:
        bounded = min(2.0, max(0.5, float(speed)))
        with self._lock:
            self._playback_speed = bounded
        return bounded

    def _run_synthesis(self, sentences: list[str], voice: str) -> None:
        assert self._audio_queue is not None
        try:
            for chunk in self._synthesize_chunks(sentences, voice):
                if self._stop_event.is_set():
                    break
                data = np.asarray(chunk, dtype=np.float32).reshape(-1)
                if data.size == 0:
                    continue
                with self._lock:
                    self._synthesized_samples += int(data.size)

                while not self._stop_event.is_set():
                    try:
                        self._audio_queue.put(data, timeout=self._queue_timeout)
                        break
                    except queue.Full:
                        continue
        except Exception as exc:
            self.last_error = exc
            with self._lock:
                self._state = PlaybackState.ERROR
            self._emit("error", PlaybackState.ERROR, str(exc))
        finally:
            try:
                self._audio_queue.put(None, timeout=self._queue_timeout)
            except queue.Full:
                pass

    def _run_audio(self) -> None:
        assert self._audio_queue is not None

        if self.state is not PlaybackState.ERROR:
            with self._lock:
                self._state = PlaybackState.PLAYING
            self._emit("state", PlaybackState.PLAYING)

        try:
            self._play_audio_queue()
        except Exception as exc:  # pragma: no cover - depends on audio device/runtime
            self.last_error = exc
            with self._lock:
                self._state = PlaybackState.ERROR
            self._emit("error", PlaybackState.ERROR, str(exc))
            return
        finally:
            with self._lock:
                if self._state is not PlaybackState.ERROR:
                    self._state = PlaybackState.IDLE
                self._cleanup_completed_locked()
            if self.state is PlaybackState.IDLE:
                self._emit("state", PlaybackState.IDLE)

    def _join_futures(self, timeout: float = 0.1) -> None:
        synthesis = self._synthesis_future
        audio = self._audio_future

        if synthesis is not None and not synthesis.done():
            try:
                synthesis.result(timeout=timeout)
            except Exception:
                pass
        if audio is not None and not audio.done():
            try:
                audio.result(timeout=timeout)
            except Exception:
                pass

    def _is_running(self) -> bool:
        with self._lock:
            return self._is_running_locked()

    def _is_running_locked(self) -> bool:
        self._cleanup_completed_locked()
        synthesis_running = self._synthesis_future is not None and not self._synthesis_future.done()
        audio_running = self._audio_future is not None and not self._audio_future.done()
        return synthesis_running or audio_running

    def _cleanup_completed_locked(self) -> None:
        if self._synthesis_future is not None and self._synthesis_future.done():
            self._synthesis_future = None
        if self._audio_future is not None and self._audio_future.done():
            self._audio_future = None
        if self._synthesis_future is None and self._audio_future is None:
            self._audio_queue = None

    def _consume_seek_samples(self) -> int:
        with self._lock:
            pending = self._seek_samples
            self._seek_samples = 0
            return pending

    def _on_audio_progress(self, sample_count: int) -> None:
        with self._lock:
            self._played_samples += max(0, int(sample_count))

    def _get_volume(self) -> float:
        with self._lock:
            return self._volume

    def _play_audio_queue(self) -> None:
        assert self._audio_queue is not None
        try:
            self.audio_player.play_from_queue(
                self._audio_queue,
                self._stop_event,
                pause_event=self._pause_event,
                volume_getter=self._get_volume,
                on_progress=self._on_audio_progress,
                consume_seek_samples=self._consume_seek_samples,
            )
        except TypeError:
            # Backward compatibility for older test doubles/custom players.
            self.audio_player.play_from_queue(self._audio_queue, self._stop_event)

    def _synthesize_chunks(self, sentences: list[str], voice: str):
        try:
            return self.backend.synthesize_sentences(sentences, voice, speed=self._playback_speed)
        except TypeError:
            return self.backend.synthesize_sentences(sentences, voice)

    def _emit(self, kind: str, state: PlaybackState, message: str = "") -> None:
        if self._on_event is None:
            return
        self._on_event(ControllerEvent(kind=kind, state=state, message=message))
