from __future__ import annotations

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
    ):
        self.backend = backend
        self.audio_player = audio_player
        self._on_event = on_event
        self._normalizer = normalizer
        self._chunker = chunker

        self._lock = threading.Lock()
        self._state = PlaybackState.IDLE
        self._audio_queue: queue.Queue[object] | None = None
        self._stop_event = threading.Event()
        self._synthesis_thread: threading.Thread | None = None
        self._audio_thread: threading.Thread | None = None
        self.last_error: Exception | None = None

    @property
    def state(self) -> PlaybackState:
        with self._lock:
            return self._state

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
            self._audio_queue = queue.Queue()
            self._stop_event = threading.Event()
            self._state = PlaybackState.SYNTHESIZING
            self._synthesis_thread = threading.Thread(
                target=self._run_synthesis,
                args=(sentences, voice),
                daemon=True,
                name="kookie-synthesis",
            )
            self._audio_thread = threading.Thread(
                target=self._run_audio,
                daemon=True,
                name="kookie-audio",
            )

            synthesis_thread = self._synthesis_thread
            audio_thread = self._audio_thread

        self._emit("state", PlaybackState.SYNTHESIZING)
        synthesis_thread.start()
        audio_thread.start()
        return True

    def stop(self) -> bool:
        with self._lock:
            running = self._is_running_locked()
            if not running and (self._audio_queue is None or self._stop_event.is_set()):
                return False
            if self._stop_event.is_set():
                return False

            self._stop_event.set()
            self._state = PlaybackState.STOPPING if running else PlaybackState.IDLE
            audio_queue = self._audio_queue

        if audio_queue is not None:
            audio_queue.put(None)

        self._emit("state", PlaybackState.STOPPING)
        return True

    def wait_until_idle(self, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            current_state = self.state
            if current_state in {PlaybackState.IDLE, PlaybackState.ERROR} and not self._is_running():
                return
            time.sleep(0.01)

        self._join_threads(timeout=0.05)

    def _run_synthesis(self, sentences: list[str], voice: str) -> None:
        assert self._audio_queue is not None
        try:
            for chunk in self.backend.synthesize_sentences(sentences, voice):
                if self._stop_event.is_set():
                    break
                self._audio_queue.put(np.asarray(chunk, dtype=np.float32))
        except Exception as exc:
            self.last_error = exc
            with self._lock:
                self._state = PlaybackState.ERROR
            self._emit("error", PlaybackState.ERROR, str(exc))
        finally:
            self._audio_queue.put(None)

    def _run_audio(self) -> None:
        assert self._audio_queue is not None

        if self.state is not PlaybackState.ERROR:
            with self._lock:
                self._state = PlaybackState.PLAYING
            self._emit("state", PlaybackState.PLAYING)

        try:
            self.audio_player.play_from_queue(self._audio_queue, self._stop_event)
        except Exception as exc:  # pragma: no cover - depends on audio device/runtime
            self.last_error = exc
            with self._lock:
                self._state = PlaybackState.ERROR
            self._emit("error", PlaybackState.ERROR, str(exc))
            return
        finally:
            self._join_threads(skip_current=True)

        with self._lock:
            if self._state is not PlaybackState.ERROR:
                self._state = PlaybackState.IDLE
        if self.state is PlaybackState.IDLE:
            self._emit("state", PlaybackState.IDLE)

    def _join_threads(self, timeout: float = 0.1, skip_current: bool = False) -> None:
        current = threading.current_thread()

        synthesis = self._synthesis_thread
        audio = self._audio_thread

        if synthesis is not None and synthesis.is_alive():
            if not skip_current or synthesis is not current:
                synthesis.join(timeout=timeout)
        if audio is not None and audio.is_alive():
            if not skip_current or audio is not current:
                audio.join(timeout=timeout)

    def _is_running(self) -> bool:
        with self._lock:
            return self._is_running_locked()

    def _is_running_locked(self) -> bool:
        synthesis_alive = self._synthesis_thread is not None and self._synthesis_thread.is_alive()
        audio_alive = self._audio_thread is not None and self._audio_thread.is_alive()
        return synthesis_alive or audio_alive

    def _emit(self, kind: str, state: PlaybackState, message: str = "") -> None:
        if self._on_event is None:
            return
        self._on_event(ControllerEvent(kind=kind, state=state, message=message))
