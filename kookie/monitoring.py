from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable


@dataclass(slots=True)
class HealthStatus:
    status: str
    backend: str
    assets_ready: bool
    details: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "backend": self.backend,
            "assets_ready": self.assets_ready,
            "details": dict(self.details),
        }


@dataclass(slots=True)
class MetricsStore:
    _values: dict[str, int] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def increment(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self._values[key] = self._values.get(key, 0) + amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._values)


def start_health_server(
    *,
    host: str,
    port: int,
    health_provider: Callable[[], HealthStatus],
    metrics_store: MetricsStore,
) -> ThreadingHTTPServer:
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                payload = health_provider().as_dict()
                self._write_json(payload)
                return
            if self.path == "/metrics":
                self._write_json(metrics_store.snapshot())
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, _format: str, *_args) -> None:
            return

        def _write_json(self, payload: dict[str, object]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="kookie-health-server")
    thread.start()
    return server
