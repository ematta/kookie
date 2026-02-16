from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .text_processing import normalize_text


@dataclass(slots=True)
class ClipboardMonitor:
    read_clipboard: Callable[[], str]
    on_new_text: Callable[[str], None]
    poll_interval: float = 0.5
    _last_clipboard: str = field(init=False, default="")
    _scheduled_event: object | None = field(init=False, default=None)

    def poll_once(self) -> str | None:
        raw = self.read_clipboard() or ""
        if raw == self._last_clipboard:
            return None

        self._last_clipboard = raw
        cleaned = normalize_text(raw)
        if not cleaned:
            return None

        self.on_new_text(cleaned)
        return cleaned

    def start(self, scheduler: Callable[[Callable[..., object], float], object]) -> None:
        self.stop()
        self._scheduled_event = scheduler(lambda *_: self.poll_once(), self.poll_interval)

    def stop(self) -> None:
        if self._scheduled_event is None:
            return

        cancel = getattr(self._scheduled_event, "cancel", None)
        if callable(cancel):
            cancel()
        self._scheduled_event = None
