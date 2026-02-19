from __future__ import annotations

from kookie.retry import RetryPolicy, retry_call


def test_retry_call_succeeds_after_transient_failures() -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def _target() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    value = retry_call(
        _target,
        policy=RetryPolicy(max_attempts=4, base_delay=0.1, factor=2.0, jitter=0.0, max_delay=1.0),
        sleeper=sleeps.append,
    )

    assert value == "ok"
    assert attempts["count"] == 3
    assert sleeps == [0.1, 0.2]


def test_retry_call_raises_after_max_attempts() -> None:
    attempts = {"count": 0}

    def _target() -> str:
        attempts["count"] += 1
        raise RuntimeError("still failing")

    try:
        retry_call(
            _target,
            policy=RetryPolicy(max_attempts=3, base_delay=0.1, factor=2.0, jitter=0.0, max_delay=1.0),
            sleeper=lambda _: None,
        )
    except RuntimeError as exc:
        assert "still failing" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected retry_call to re-raise after max attempts")

    assert attempts["count"] == 3
