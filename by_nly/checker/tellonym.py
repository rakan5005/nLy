"""Tellonym availability checker — fresh session per check, auto-retry on failure."""

import asyncio as _asyncio
from curl_cffi.requests import AsyncSession as CurlAsyncSession

from .base import BaseChecker
from ..models.enums import Platform, Status

MAX_CONCURRENT = 20


class TellonymChecker(BaseChecker):
    platform = Platform.TELLONYM
    max_retries = 1

    def __init__(self, session):
        self._session = session
        self._sem = _asyncio.Semaphore(MAX_CONCURRENT)

    async def ensure_connected(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def _try_check(self, username: str) -> tuple[Status, str]:
        proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        saf = None
        try:
            saf = CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
            r = await saf.get(
                "https://tellonym.me/api/accounts/check",
                params={"username": username},
                headers={"Accept": "application/json", "Referer": "https://tellonym.me/"},
                timeout=5,
            )
            if r.status_code == 429:
                return Status.RATE_LIMITED, "rate limited"

            if r.status_code == 200:
                try:
                    data = r.json()
                    available = data.get("username")
                    if available is True:
                        return Status.AVAILABLE, "api: available"
                    elif available is False:
                        return Status.TAKEN, "api: taken"
                except Exception:
                    pass

            if r.status_code in (403, 503):
                return Status.UNKNOWN, "blocked"

            return Status.UNKNOWN, f"HTTP {r.status_code}"

        except Exception:
            return Status.UNKNOWN, "request failed"
        finally:
            if saf:
                try:
                    await saf.close()
                except Exception:
                    pass

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        async with self._sem:
            result = await self._try_check(username)
            if result[0] not in (Status.UNKNOWN, Status.RATE_LIMITED):
                return result
            return await self._try_check(username)
