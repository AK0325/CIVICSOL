"""
CIVICSOL - Distributed Rate Limiter & Brute-Force Protection
Supports Redis-backed distributed sliding window across multiple Uvicorn/Gunicorn workers,
with transparent, automatic fallback to thread-safe in-memory rate limiting when Redis is unavailable.
"""

import logging
import os
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import HTTPException, status

logger = logging.getLogger("civicsol.rate_limiter")


class SlidingWindowRateLimiter:
    """
    Hybrid sliding-window rate limiter.
    Uses Redis sorted sets (ZADD/ZREMRANGEBYSCORE/ZCARD) when Redis is connected;
    falls back seamlessly to thread-safe in-memory tracking if Redis is unreachable.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self._lock = Lock()
        self._records: Dict[str, List[float]] = defaultdict(list)
        self._redis = None
        self._redis_prefix = "civicsol:ratelimit:"

        # Try connecting to Redis if available
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis
            client = redis.Redis.from_url(
                url,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                decode_responses=True,
            )
            client.ping()
            self._redis = client
            logger.info("SlidingWindowRateLimiter: Connected to Redis for distributed rate limiting.")
        except Exception as exc:
            self._redis = None
            logger.info(f"SlidingWindowRateLimiter: Operating in thread-safe in-memory fallback mode ({type(exc).__name__}).")

    @property
    def is_distributed(self) -> bool:
        """Returns True if Redis is actively connected."""
        return self._redis is not None

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

        # 1. Distributed Redis Path
        if self._redis is not None:
            rkey = f"{self._redis_prefix}{key}"
            try:
                pipe = self._redis.pipeline(transaction=True)
                pipe.zremrangebyscore(rkey, 0, now - window_seconds)
                pipe.zcard(rkey)
                pipe.zrange(rkey, 0, 0, withscores=True)
                _, count, oldest_items = pipe.execute()

                if count >= max_attempts:
                    oldest_score = oldest_items[0][1] if oldest_items else now - window_seconds
                    retry_after = int(window_seconds - (now - oldest_score)) + 1
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many failed attempts. Brute-force protection active. Try again in {max(1, retry_after)} seconds.",
                        headers={"Retry-After": str(max(1, retry_after))},
                    )
                return
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(f"Redis rate check error; falling back to memory: {exc}")

        # 2. In-Memory Fallback Path
        with self._lock:
            timestamps = self._records[key]
            valid_timestamps = [t for t in timestamps if now - t < window_seconds]
            if valid_timestamps:
                self._records[key] = valid_timestamps
            elif key in self._records:
                del self._records[key]

            if len(valid_timestamps) >= max_attempts:
                oldest = valid_timestamps[0]
                retry_after = int(window_seconds - (now - oldest)) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed attempts. Brute-force protection active. Try again in {max(1, retry_after)} seconds.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )

    def record_attempt(self, key: str, window_seconds: int = 300) -> None:
        """Record a failed attempt timestamp for the key."""
        now = time.time()

        if self._redis is not None:
            rkey = f"{self._redis_prefix}{key}"
            try:
                pipe = self._redis.pipeline(transaction=True)
                pipe.zadd(rkey, {f"{now}:{uuid4().hex[:6]}": now})
                pipe.expire(rkey, window_seconds * 2)
                pipe.execute()
                return
            except Exception as exc:
                logger.warning(f"Redis record attempt error; falling back to memory: {exc}")

        with self._lock:
            self._records[key].append(now)

    def reset(self, key: str) -> None:
        """Clear recorded attempts on successful authentication."""
        if self._redis is not None:
            try:
                self._redis.delete(f"{self._redis_prefix}{key}")
            except Exception:
                pass

        with self._lock:
            if key in self._records:
                del self._records[key]

    def clear_all(self) -> None:
        """Clear all entries (useful in testing fixtures)."""
        if self._redis is not None:
            try:
                keys = self._redis.keys(f"{self._redis_prefix}*")
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                pass

        with self._lock:
            self._records.clear()


# Central singleton instances
login_rate_limiter = SlidingWindowRateLimiter()
