"""Tellonym availability checker — session pool for reliable concurrency."""

import asyncio as _asyncio
from curl_cffi.requests import AsyncSession as CurlAsyncSession

from .base import BaseChecker
from ..models.enums import Platform, Status


POOL_SIZE = 15


class TellonymChecker(BaseChecker):
    platform = Platform.TELLONYM
    max_retries = 1

    def __init__(self, session):
        self._session = session
        self._pool: list[CurlAsyncSession] = []
        self._pool_lock = _asyncio.Lock()
        self._sem = _asyncio.Semaphore(POOL_SIZE)

    async def ensure_connected(self) -> None:
        proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        for _ in range(POOL_SIZE):
            try:
                self._pool.append(CurlAsyncSession(impersonate="safari17_0", proxies=proxies))
            except Exception:
                pass

    async def disconnect(self) -> None:
        for saf in self._pool:
            try:
                await saf.close()
            except Exception:
                pass
        self._pool.clear()

    async def _borrow(self) -> CurlAsyncSession | None:
        async with self._pool_lock:
            if self._pool:
                return self._pool.pop()
        proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        try:
            return CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
        except Exception:
            return None

    async def _give_back(self, saf: CurlAsyncSession) -> None:
        async with self._pool_lock:
            if len(self._pool) < POOL_SIZE:
                self._pool.append(saf)
            else:
                try:
                    await saf.close()
                except Exception:
                    pass

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        async with self._sem:
            saf = await self._borrow()
            if not saf:
                return Status.UNKNOWN, "no session"

            try:
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
                await self._give_back(saf)
