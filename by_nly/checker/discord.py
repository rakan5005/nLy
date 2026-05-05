"""Discord availability checker — auth/register endpoint with auto-reconnect.

Discord rate-limits aggressively. Auto-reconnects every N checks.
No DISCORD_TOKEN required.
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
RECONNECT_EVERY = 8
MAX_CONCURRENT = 6


class DiscordChecker(BaseChecker):
    platform = Platform.DISCORD
    max_retries = 1

    def __init__(self, session):
        self._session = session
        self._safari = None
        self._token = os.environ.get("DISCORD_TOKEN", "").strip()
        self._check_count = 0
        self._reconnect_lock = _asyncio.Lock()
        self._concurrency = _asyncio.Semaphore(MAX_CONCURRENT)

    async def ensure_connected(self) -> None:
        try:
            proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            self._safari = CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
            self._check_count = 0
        except Exception:
            self._safari = None

    async def disconnect(self) -> None:
        if self._safari:
            try:
                await self._safari.close()
            except Exception:
                pass
            self._safari = None

    async def _maybe_reconnect(self) -> None:
        self._check_count += 1
        if self._check_count >= RECONNECT_EVERY:
            async with self._reconnect_lock:
                if self._check_count >= RECONNECT_EVERY:
                    if self._safari:
                        try:
                            await self._safari.close()
                        except Exception:
                            pass
                    try:
                        proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
                        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
                        self._safari = CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
                    except Exception:
                        pass
                    self._check_count = 0

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        async with self._concurrency:
            await self._maybe_reconnect()

            url = "https://discord.com/api/v9/auth/register"
            headers = {
                "User-Agent": SAFARI_UA,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/json",
                "Origin": "https://discord.com",
                "Referer": "https://discord.com/register",
                "X-Debug-Options": "bugReporterEnabled",
                "X-Discord-Locale": "en-US",
            }
            try:
                r = await self._safari.post(
                    url,
                    headers=headers,
                    json={
                        "email": f"{username}@check.example.com",
                        "username": username,
                        "password": STRONG_PASS,
                        "date_of_birth": "2000-01-01",
                        "consent": True,
                        "captcha_key": None,
                    },
                    timeout=6,
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

                if r.status_code == 429:
                    return Status.RATE_LIMITED, "register: rate limited"

                return Status.UNKNOWN, f"register: HTTP {r.status_code}"
            except Exception as e:
                return Status.UNKNOWN, str(e)[:100]
