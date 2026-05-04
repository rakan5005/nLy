"""Base availability checker with retry logic and exponential backoff."""

import asyncio
import time
from abc import ABC, abstractmethod
from ..models.enums import Platform, Status
from ..models.results import CheckResult


class BaseChecker(ABC):
    platform: Platform
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0

    @abstractmethod
    async def _check_availability(self, username: str) -> tuple[Status, str]:
        ...

    async def ensure_connected(self) -> None:
        """Optional hook called before starting checks (e.g. MTProto connect)."""
        pass

    async def disconnect(self) -> None:
        """Optional cleanup hook called after checks finish."""
        pass

    async def check(self, username: str) -> CheckResult:
        start = time.monotonic()
        last_reason = ""
        for attempt in range(self.max_retries):
            try:
                status, reason = await self._check_availability(username)
                elapsed = (time.monotonic() - start) * 1000
                return CheckResult(
                    platform=self.platform,
                    username=username,
                    status=status,
                    reason=reason,
                    response_time_ms=elapsed,
                )
            except asyncio.TimeoutError:
                last_reason = "timeout"
            except Exception as e:
                last_reason = str(e)[:200]

            if attempt < self.max_retries - 1:
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                await asyncio.sleep(delay)

        elapsed = (time.monotonic() - start) * 1000
        return CheckResult(
            platform=self.platform,
            username=username,
            status=Status.UNKNOWN,
            reason=f"all {self.max_retries} retries failed: {last_reason}",
            response_time_ms=elapsed,
        )
