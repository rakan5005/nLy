"""Discord availability checker — session pool for maximum speed.

Pre-creates a pool of Safari sessions, reused across checks.
No per-check session creation overhead. 20 concurrent max.
No Discord token required.
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
POOL_SIZE = 20


class DiscordChecker(BaseChecker):
    platform = Platform.DISCORD
    max_retries = 1

    def __init__(self, session):
        self._session = session
        self._token = os.environ.get("DISCORD_TOKEN", "").strip()
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

    async def _get_session(self) -> CurlAsyncSession | None:
        async with self._pool_lock:
            if self._pool:
                return self._pool.pop()
        proxy_url = self._session._proxy if hasattr(self._session, "_proxy") else None
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        try:
            return CurlAsyncSession(impersonate="safari17_0", proxies=proxies)
        except Exception:
            return None

    async def _put_session(self, saf: CurlAsyncSession) -> None:
        async with self._pool_lock:
            if len(self._pool) < POOL_SIZE:
                self._pool.append(saf)
            else:
                try:
                    await saf.close()
                except Exception:
                    pass

    async def _try_register(self, username: str) -> tuple[Status, str]:
        saf = await self._get_session()
        if not saf:
            return Status.UNKNOWN, "no session available"

        try:
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
                timeout=4,
            )

            if r.status_code == 400:
                data = r.json()
                errors = data.get("errors", {})
                username_errs = errors.get("username", {}).get("_errors", [])
                for e in username_errs:
                    code = e.get("code", "")
                    msg = e.get("message", "").lower()
                    if any(k in code.lower() or k in msg for k in ("taken", "already", "unavailable")):
                        await self._put_session(saf)
                        return Status.TAKEN, f"register: {msg[:60]}"

                if data.get("captcha_key"):
                    await self._put_session(saf)
                    return Status.AVAILABLE, "register: available (passed validation)"

                await self._put_session(saf)
                return Status.UNKNOWN, f"register: {str(data)[:80]}"

            if r.status_code in (429, 403):
                await self._put_session(saf)
                return Status.RATE_LIMITED, f"register: HTTP {r.status_code}"

            await self._put_session(saf)
            return Status.UNKNOWN, f"register: HTTP {r.status_code}"

        except Exception as e:
            await self._put_session(saf)
            return Status.UNKNOWN, str(e)[:60]

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        async with self._sem:
            result = await self._try_register(username)
            if result[0] not in (Status.UNKNOWN, Status.RATE_LIMITED):
                return result

            return await self._try_register(username)
