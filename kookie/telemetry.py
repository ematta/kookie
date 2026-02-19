from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(slots=True)
class LocalTelemetry:
    enabled: bool
    output_path: Path
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def record(self, event: str, data: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return

        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "data": data or {},
        }

        with self._lock:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, sort_keys=True) + "\n")
