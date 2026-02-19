from __future__ import annotations

from kookie.monitoring import HealthStatus, MetricsStore


def test_metrics_store_tracks_counters() -> None:
    metrics = MetricsStore()
    metrics.increment("play_started")
    metrics.increment("play_started")
    metrics.increment("save_completed")

    snapshot = metrics.snapshot()
    assert snapshot["play_started"] == 2
    assert snapshot["save_completed"] == 1


def test_health_status_serializes_runtime_summary() -> None:
    health = HealthStatus(
        status="ok",
        backend="mock",
        assets_ready=True,
        details={"voice": "available"},
    )

    payload = health.as_dict()
    assert payload["status"] == "ok"
    assert payload["backend"] == "mock"
    assert payload["assets_ready"] is True
    assert payload["details"]["voice"] == "available"
