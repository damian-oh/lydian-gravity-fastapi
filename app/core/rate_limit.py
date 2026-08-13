"""Generic in-memory sliding-window rate limiting, keyed per caller.

The same shape as the demo-session throttle in app.services.demo_service
(lock-protected deque of timestamps per key), generalized so unrelated
endpoints can each get an independent ceiling without duplicating the
pruning/locking/eviction logic. Single-process, in-memory -- fine for the
single-instance deployment this project targets, not for multiple workers.
"""

import threading
import time
from collections import deque

# Ceiling on how many distinct keys a throttle tracks at once. When idle keys
# alone cannot bring the dict back under it, the stalest active keys are
# evicted too -- costing accuracy for them, never unbounded memory, which a
# caller rotating source addresses could otherwise inflate at will.
KEY_TRACKING_LIMIT = 1024


class RateLimitExceeded(RuntimeError):
    """Raised when a throttle's ceiling is reached for a key."""


class SlidingWindowThrottle:
    def __init__(self, tracking_limit: int = KEY_TRACKING_LIMIT) -> None:
        self._tracking_limit = tracking_limit
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, max_hits: int, window_seconds: int) -> None:
        """Record an attempt for key, raising RateLimitExceeded past max_hits.

        max_hits and window_seconds are per-call so the throttle holds no
        config state and runtime setting overrides (e.g. in tests) take effect.
        """
        with self._lock:
            now = time.monotonic()
            cutoff = now - window_seconds

            window = self._hits.setdefault(key, deque())
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= max_hits:
                raise RateLimitExceeded

            window.append(now)

            if len(self._hits) > self._tracking_limit:
                self._evict(cutoff)

    def _evict(self, cutoff: float) -> None:
        """Bring the key dict back under the tracking limit.

        Idle keys (all entries aged out) go first; if that is not enough, the
        stalest active keys follow. Callers must hold _lock. The key hit just
        now has the newest entry, so it is never evicted here.
        """
        for key in list(self._hits):
            window = self._hits[key]
            while window and window[0] < cutoff:
                window.popleft()

            if not window:
                del self._hits[key]

        overflow = len(self._hits) - self._tracking_limit

        if overflow > 0:
            stalest = sorted(
                self._hits,
                key=lambda key: self._hits[key][-1],
            )[:overflow]

            for key in stalest:
                del self._hits[key]

    def reset(self) -> None:
        """Clear all tracked hits. Used by tests."""
        with self._lock:
            self._hits.clear()
