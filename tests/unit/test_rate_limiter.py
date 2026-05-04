"""Tests for rate limiter and cache."""

import pytest
import time
from by_nly.rate_limiter.token_bucket import TokenBucket, AdaptiveController
from by_nly.cache.cache import Cache


class TestTokenBucket:
    @pytest.mark.asyncio
    async def test_acquire(self):
        bucket = TokenBucket(rate=10.0, burst=5)
        start = time.monotonic()
        for _ in range(10):
            await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 2.0  # Should be fast due to burst

    @pytest.mark.asyncio
    async def test_slow_rate(self):
        bucket = TokenBucket(rate=2.0, burst=1)
        start = time.monotonic()
        for _ in range(4):
            await bucket.acquire()
        elapsed = time.monotonic() - start
        assert elapsed > 0.5  # Should take time to refill


class TestAdaptiveController:
    def test_initial_concurrency(self):
        ac = AdaptiveController(base_concurrency=10, max_concurrency=20)
        assert 1 <= ac.concurrency <= 20

    def test_decrease_on_rate_limit(self):
        ac = AdaptiveController(base_concurrency=10, max_concurrency=20)
        before = ac.concurrency
        ac.report_rate_limited(retry_after=10.0)
        assert ac.concurrency <= before

    def test_increase_on_success(self):
        ac = AdaptiveController(base_concurrency=10, max_concurrency=20)
        ac.current = 3
        ac.base = 10
        for _ in range(20):
            ac.report_success()
        assert ac.concurrency >= 3

    def test_never_below_one(self):
        ac = AdaptiveController(base_concurrency=10, max_concurrency=20)
        for _ in range(50):
            ac.report_rate_limited(retry_after=1.0)
        assert ac.concurrency >= 1


class TestCache:
    def test_set_get(self):
        c = Cache(max_size=100)
        c.set("key1", "value1")
        assert c.get("key1") == "value1"

    def test_miss(self):
        c = Cache(max_size=100)
        assert c.get("nonexistent") is None

    def test_eviction(self):
        c = Cache(max_size=3)
        c.set("a", "1")
        c.set("b", "2")
        c.set("c", "3")
        c.set("d", "4")  # Should evict "a"
        assert c.get("a") is None
        assert c.get("b") == "2"

    def test_hits_misses(self):
        c = Cache(max_size=10)
        c.set("x", "v")
        c.get("x")
        c.get("x")
        c.get("y")
        assert c.hits == 2
        assert c.misses == 1

    def test_overwrite(self):
        c = Cache(max_size=10)
        c.set("k", "old")
        c.set("k", "new")
        assert c.get("k") == "new"
        assert c.size == 1
