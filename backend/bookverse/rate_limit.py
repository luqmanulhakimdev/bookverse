from collections import defaultdict, deque
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, window_seconds: float = 60):
        self.window_seconds = window_seconds
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def allow(self, client: str, bucket_name: str, limit: int, now: float | None = None) -> bool:
        timestamp = monotonic() if now is None else now
        bucket = self._events[(client, bucket_name)]
        while bucket and bucket[0] <= timestamp - self.window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(timestamp)
        if len(self._events) > 10000:
            cutoff = timestamp - self.window_seconds
            for key in list(self._events):
                events = self._events[key]
                while events and events[0] <= cutoff:
                    events.popleft()
                if not events:
                    del self._events[key]
        return True
