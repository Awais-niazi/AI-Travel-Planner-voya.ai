from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic


class RateLimitService:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = monotonic()
        bucket = self._buckets[key]
        cutoff = now - window_seconds

        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= max_requests:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return False, retry_after

        bucket.append(now)
        return True, 0

    def reset(self) -> None:
        self._buckets.clear()


rate_limiter = RateLimitService()
