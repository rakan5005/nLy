"""Snapchat availability checker — parallel web + Bitmoji API fallback."""

import asyncio

from .base import BaseChecker
from ..models.enums import Platform, Status

SNAPCHAT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class SnapchatChecker(BaseChecker):
    platform = Platform.SNAPCHAT
    max_retries = 1

    def __init__(self, session):
        self._session = session

    async def _check_via_bitmoji(self, username: str) -> tuple[Status, str] | None:
        url = f"https://bitmoji.api.snapchat.com/api/user/find?username={username}"
        try:
            async with self._session.get(
                url, headers={"User-Agent": SNAPCHAT_UA, "Accept": "application/json"},
                timeout=6, allow_redirects=True,
            ) as resp:
                if resp.status == 200:
                    return Status.TAKEN, "bitmoji: user found"
                elif resp.status == 404:
                    return Status.AVAILABLE, "bitmoji: no user"
                return None
        except Exception:
            return None

    async def _check_via_web(self, username: str) -> tuple[Status, str] | None:
        url = f"https://www.snapchat.com/add/{username}"
        try:
            async with self._session.get(
                url, headers={"User-Agent": SNAPCHAT_UA}, timeout=8, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    not_found_indicators = [
                        "could not be found", "this content doesn't exist",
                        "Sorry, we couldn't find", "doesn't exist",
                    ]
                    if any(ind in text for ind in not_found_indicators):
                        return Status.AVAILABLE, "web: user not found"
                    return Status.TAKEN, "web: profile exists"
                elif resp.status == 404:
                    return Status.AVAILABLE, "web: 404"
                return None
        except Exception:
            return None

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        web_task = asyncio.create_task(self._check_via_web(username))
        bitmoji_task = asyncio.create_task(self._check_via_bitmoji(username))

        web_result = await web_task
        if web_result:
            bitmoji_task.cancel()
            return web_result

        bitmoji_result = await bitmoji_task
        if bitmoji_result:
            return bitmoji_result

        return Status.UNKNOWN, "all methods blocked (use proxy)"
