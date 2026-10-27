"""In-memory fixed-window rate limits (CONTRACT §3, spec N10).

No new dependency and no shared store: fine for one API instance. Counts reset when the API
restarts.
"""

import time
from collections.abc import Callable
from datetime import timedelta

MAX_KEYS = 10_000  # expired windows are dropped once this many keys are tracked


class FixedWindowLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        # (scope, key) → (window start, window length in s, requests so far)
        self._windows: dict[tuple[str, str], tuple[float, float, int]] = {}

    def hit(self, scope: str, key: str, limit: int, window: timedelta) -> float | None:
        """Count one request. None if it is allowed, else seconds until the window resets."""
        now = self._clock()
        length = window.total_seconds()
        start, _, count = self._windows.get((scope, key), (now, length, 0))
        if now - start >= length:
            start, count = now, 0
        if count >= limit:
            return start + length - now
        if len(self._windows) >= MAX_KEYS:
            self._prune(now)
        self._windows[(scope, key)] = (start, length, count + 1)
        return None

    def reset(self) -> None:
        self._windows.clear()

    def _prune(self, now: float) -> None:
        self._windows = {k: v for k, v in self._windows.items() if now - v[0] < v[1]}


limiter = FixedWindowLimiter()
