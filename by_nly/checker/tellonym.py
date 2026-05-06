"""Tellonym availability checker — Safari impersonation bypasses Cloudflare."""

import asyncio as _asyncio
from curl_cffi.requests import AsyncSession as CurlAsyncSession

from .base import BaseChecker
from ..models.enums import Platform, Status


class TellonymChecker(BaseChecker):
    platform = Platform.TELLONYM
    max_retries = 2
    base_delay = 1.0

    def __init__(self, session):
        self._session = session
        self._safari = None

    async def ensure_connected(self) -> None:
        try:
            proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            self._safari = CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
        except Exception:
            self._safari = None

    async def disconnect(self) -> None:
        if self._safari:
            try:
                await self._safari.close()
            except Exception:
                pass
            self._safari = None

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        if not self._safari:
            return Status.UNKNOWN, "no Safari session"

        try:
            r = await self._safari.get(
                "https://tellonym.me/api/accounts/check",
                params={"username": username},
                headers={"Accept": "application/json", "Referer": "https://tellonym.me/"},
                timeout=4,
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
