from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.5
    factor: float = 2.0
    jitter: float = 0.2
    max_delay: float = 5.0


def retry_call[T](
    func: Callable[[], T],
    *,
    policy: RetryPolicy | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    randomizer: Callable[[], float] = random.random,
) -> T:
    selected_policy = policy or RetryPolicy()
    attempts = 0
    delay = selected_policy.base_delay

    while True:
        attempts += 1
        try:
            return func()
        except Exception:
            if attempts >= selected_policy.max_attempts:
                raise
            jitter_factor = (randomizer() * 2.0 - 1.0) * selected_policy.jitter
            bounded_delay = min(selected_policy.max_delay, max(0.0, delay * (1.0 + jitter_factor)))
            sleeper(bounded_delay)
            delay = min(selected_policy.max_delay, delay * selected_policy.factor)
