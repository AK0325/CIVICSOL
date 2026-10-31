"""
Unit and integration tests for CIVICSOL Distributed & Hybrid Rate Limiter.
Verifies:
1. In-memory sliding window rate limiting.
2. Redis-backed distributed rate limiting across separate worker instances.
3. Fail-safe fallback when Redis is disconnected.
"""

import multiprocessing
import os
import unittest
from fastapi import HTTPException

from backend.core.rate_limiter import SlidingWindowRateLimiter


def _worker_record_attempt(key: str):
    limiter = SlidingWindowRateLimiter()
    limiter.record_attempt(key, window_seconds=60)


def _worker_check_limit(key: str, max_attempts: int, queue: multiprocessing.Queue):
    limiter = SlidingWindowRateLimiter()
    try:
        limiter.check_and_record(key, max_attempts=max_attempts, window_seconds=60)
        queue.put("ALLOWED")
    except HTTPException as exc:
        queue.put(f"BLOCKED:{exc.status_code}")


class TestDistributedRateLimiter(unittest.TestCase):

    def setUp(self):
        self.in_memory_limiter = SlidingWindowRateLimiter(redis_url="redis://localhost:9999/9")  # Nonexistent
        self.assertFalse(self.in_memory_limiter.is_distributed)

    def test_01_in_memory_rate_limiting(self):
        """In-memory limiter blocks after max_attempts and resets on success."""
        key = "test_in_memory_user"
        self.in_memory_limiter.reset(key)

        for _ in range(3):
            self.in_memory_limiter.check_and_record(key, max_attempts=3, window_seconds=60)
            self.in_memory_limiter.record_attempt(key)

        # 4th check should raise HTTP 429
        with self.assertRaises(HTTPException) as ctx:
            self.in_memory_limiter.check_and_record(key, max_attempts=3, window_seconds=60)
        self.assertEqual(ctx.exception.status_code, 429)

        # Reset
        self.in_memory_limiter.reset(key)
        # Should be allowed again
        self.in_memory_limiter.check_and_record(key, max_attempts=3, window_seconds=60)

    def test_02_redis_distributed_across_workers(self):
        """Separate worker processes share state via Redis and enforce distributed rate limits."""
        redis_limiter = SlidingWindowRateLimiter()
        if not redis_limiter.is_distributed:
            self.skipTest("Redis container not accessible; skipping multi-worker distributed test.")

        test_key = "test_multiworker_user"
        redis_limiter.reset(test_key)

        # Worker 1 records attempt 1
        p1 = multiprocessing.Process(target=_worker_record_attempt, args=(test_key,))
        p1.start()
        p1.join()

        # Worker 2 records attempt 2
        p2 = multiprocessing.Process(target=_worker_record_attempt, args=(test_key,))
        p2.start()
        p2.join()

        # Worker 3 checks if max_attempts=2 was hit
        q = multiprocessing.Queue()
        p3 = multiprocessing.Process(target=_worker_check_limit, args=(test_key, 2, q))
        p3.start()
        p3.join()

        result = q.get(timeout=5)
        self.assertEqual(result, "BLOCKED:429")

        # Cleanup
        redis_limiter.reset(test_key)


if __name__ == "__main__":
    unittest.main()

