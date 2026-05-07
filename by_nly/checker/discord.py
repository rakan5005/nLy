"""Discord availability checker — rotating proxy support for max speed.

Without proxy: 8 concurrent (safe limit for single IP).
With proxy: 40 concurrent (each request gets a different IP via rotation).
Supports both rotating gateway proxy and proxy file with multiple URLs.
"""

import asyncio as _asyncio
import os

from curl_cffi.requests import AsyncSession as CurlAsyncSession

from .base import BaseChecker
from ..models.enums import Platform, Status

SAFARI_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)

STRONG_PASS = "Xy9#mK2!pQ5$vL8@nR3#aB1"
NO_PROXY_CONCURRENT = 8
PROXY_CONCURRENT = 40


class DiscordChecker(BaseChecker):
    platform = Platform.DISCORD
    max_retries = 1

    def __init__(self, session, proxy_manager=None):
        self._session = session
        self._proxy_manager = proxy_manager
        self._token = os.environ.get("DISCORD_TOKEN", "").strip()
        base_proxy = self._session._proxy if hasattr(self._session, "_proxy") else None
        self._has_proxy = bool(base_proxy or (proxy_manager and proxy_manager.alive_count > 0))
        self._concurrent = PROXY_CONCURRENT if self._has_proxy else NO_PROXY_CONCURRENT
        self._sem = _asyncio.Semaphore(self._concurrent)

    async def ensure_connected(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def _get_proxy(self) -> str | None:
        if self._proxy_manager and self._proxy_manager.alive_count > 0:
            p = await self._proxy_manager.get_next()
            if p:
                return p.url
        return self._session._proxy if hasattr(self._session, "_proxy") else None

    async def _try_register(self, username: str) -> tuple[Status, str]:
        proxy_url = await self._get_proxy()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        saf = None
        try:
            saf = CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
            r = await saf.post(
                "https://discord.com/api/v9/auth/register",
                headers={
                    "User-Agent": SAFARI_UA,
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Content-Type": "application/json",
                    "Origin": "https://discord.com",
                    "Referer": "https://discord.com/register",
                    "X-Debug-Options": "bugReporterEnabled",
                    "X-Discord-Locale": "en-US",
                },
                json={
                    "email": f"{username}@check.example.com",
                    "username": username,
                    "password": STRONG_PASS,
                    "date_of_birth": "2000-01-01",
                    "consent": True,
                    "captcha_key": None,
                },
                timeout=3,
            )

            if r.status_code == 400:
                data = r.json()
                errors = data.get("errors", {})
                username_errs = errors.get("username", {}).get("_errors", [])
                for e in username_errs:
                    code = e.get("code", "")
                    msg = e.get("message", "").lower()
                    if any(k in code.lower() or k in msg for k in ("taken", "already", "unavailable")):
                        return Status.TAKEN, f"register: {msg[:60]}"

                if data.get("captcha_key"):
                    return Status.AVAILABLE, "register: available (passed validation)"

                return Status.UNKNOWN, f"register: {str(data)[:80]}"

            if r.status_code in (429, 403):
                return Status.RATE_LIMITED, f"register: HTTP {r.status_code}"

            return Status.UNKNOWN, f"register: HTTP {r.status_code}"

        except Exception as e:
            return Status.UNKNOWN, str(e)[:60]
        finally:
            if saf:
                try:
                    await saf.close()
                except Exception:
                    pass

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        async with self._sem:
            result = await self._try_register(username)
            if result[0] not in (Status.UNKNOWN, Status.RATE_LIMITED):
                return result
            return await self._try_register(username)
