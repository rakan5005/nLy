"""Token bucket rate limiter with adaptive concurrency control."""

import asyncio
import time


class TokenBucket:
    def __init__(
        self,
        rate: float,
        burst: int,
        safe_mode_factor: float = 1.0,
    ):
        self.rate = rate * safe_mode_factor
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_refill = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait)


class AdaptiveController:
    def __init__(
        self,
        base_concurrency: int,
        max_concurrency: int,
        safe_mode_factor: float = 1.0,
    ):
        self.base = base_concurrency
        self.max = max_concurrency
        self.current = max(1, int(base_concurrency * safe_mode_factor))
        self.rate_limited_count = 0
        self.success_count = 0
        self._window = 50

    def report_success(self) -> None:
        self.success_count += 1
        self.rate_limited_count = max(0, self.rate_limited_count - 0.5)
        if self.success_count % 20 == 0 and self.current < self.base:
            self.current = min(self.current + 1, self.max)

    def report_rate_limited(self, retry_after: float = 1.0) -> None:
        self.rate_limited_count += 1
        self.current = max(1, self.current - 1)
        if retry_after > 5:
            self.current = max(1, self.current // 2)

    @property
    def concurrency(self) -> int:
        return self.current
