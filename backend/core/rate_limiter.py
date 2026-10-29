"""
CIVICSOL - Rate Limiter & Brute-Force Protection
Thread-safe sliding window rate limiter for login and sensitive authentication endpoints.
"""

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List
from fastapi import HTTPException, status


class SlidingWindowRateLimiter:
    """
    Sliding window in-memory rate limiter.
    Safely purges expired timestamps and checks rate limits.
    """

    def __init__(self):
        self._lock = Lock()
        self._records: Dict[str, List[float]] = defaultdict(list)

    def check_and_record(
        self,
        key: str,
        max_attempts: int = 5,
        window_seconds: int = 300,
    ) -> None:
        """
        Check if the key has exceeded max_attempts within window_seconds.
        If exceeded, raises HTTP 429 Too Many Requests.
        Otherwise, does NOT record an attempt until record_attempt is explicitly called.
        """
        now = time.time()
        with self._lock:
            # Purge timestamps outside the window
            timestamps = self._records[key]
            valid_timestamps = [t for t in timestamps if now - t < window_seconds]
            self._records[key] = valid_timestamps

            if len(valid_timestamps) >= max_attempts:
                oldest = valid_timestamps[0]
                retry_after = int(window_seconds - (now - oldest)) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Brute-force protection active. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )

    def record_attempt(self, key: str) -> None:
        """Record a failed attempt timestamp for the key."""
        now = time.time()
        with self._lock:
            self._records[key].append(now)

    def reset(self, key: str) -> None:
        """Clear recorded attempts on successful authentication."""
        with self._lock:
            if key in self._records:
                del self._records[key]

    def clear_all(self) -> None:
        """Clear all entries (useful in testing fixtures)."""
        with self._lock:
            self._records.clear()


# Central singleton instances
login_rate_limiter = SlidingWindowRateLimiter()
