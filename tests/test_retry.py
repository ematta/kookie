from __future__ import annotations

import pytest

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

    with pytest.raises(RuntimeError, match="still failing"):
        retry_call(
            _target,
            policy=RetryPolicy(max_attempts=3, base_delay=0.1, factor=2.0, jitter=0.0, max_delay=1.0),
            sleeper=lambda _: None,
        )

    assert attempts["count"] == 3


def test_retry_call_applies_jitter_to_sleep_delays() -> None:
    """Jitter with randomizer=0.0 gives jitter_factor=-0.5, shrinking each delay by half."""
    sleeps: list[float] = []
    attempts = {"count": 0}

    def _target() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    # randomizer() == 0.0  →  jitter_factor = (0.0*2.0 - 1.0) * 0.5 = -0.5
    # sleep 1: min(1.0, max(0.0, 0.1 * 0.5)) = 0.05   (base_delay=0.1)
    # sleep 2: min(1.0, max(0.0, 0.2 * 0.5)) = 0.10   (delay grows to 0.2 after factor)
    retry_call(
        _target,
        policy=RetryPolicy(max_attempts=4, base_delay=0.1, factor=2.0, jitter=0.5, max_delay=1.0),
        sleeper=sleeps.append,
        randomizer=lambda: 0.0,
    )

    assert sleeps == pytest.approx([0.05, 0.10])
