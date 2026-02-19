from __future__ import annotations

import json
from pathlib import Path

from kookie.telemetry import LocalTelemetry


def test_local_telemetry_writes_events_when_enabled(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.jsonl"
    telemetry = LocalTelemetry(enabled=True, output_path=path)

    telemetry.record("play_started", {"voice": "af_sarah"})

    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "play_started"
    assert payload["data"]["voice"] == "af_sarah"


def test_local_telemetry_is_noop_when_disabled(tmp_path: Path) -> None:
    path = tmp_path / "telemetry.jsonl"
    telemetry = LocalTelemetry(enabled=False, output_path=path)

    telemetry.record("play_started", {"voice": "af_sarah"})

    assert not path.exists()
