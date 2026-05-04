"""X (Twitter) availability checker via bot UA scrapers + Nitter fallback."""

import re

from .base import BaseChecker
from ..models.enums import Platform, Status

TWITTER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

BOT_UA = "Twitterbot/1.0"

NITTER_INSTANCES = [
    "nitter.net",
    "nitter.space",
    "nitter.privacydev.net",
    "nitter.nl",
    "nitter.it",
    "nitter.poast.org",
    "nitter.mint.lgbt",
    "nitter.kavin.rocks",
]


class TwitterChecker(BaseChecker):
    platform = Platform.TWITTER

    def __init__(self, session):
        self._session = session

    async def _check_via_x(self, username: str) -> tuple[Status, str] | None:
        url = f"https://x.com/{username}"
        headers = {"User-Agent": BOT_UA}
        try:
            async with self._session.get(
                url, headers=headers, timeout=10, allow_redirects=True
            ) as resp:
                if resp.status == 404:
                    return Status.AVAILABLE, "x.com: 404 (bot UA)"
                elif resp.status == 200:
                    text = await resp.text()
                    if "This account doesn" in text:
                        return Status.AVAILABLE, "x.com: account not found"
                    return Status.TAKEN, "x.com: profile exists"
                elif resp.status == 429:
                    return Status.RATE_LIMITED, "x.com: rate limited"
                return Status.UNKNOWN, f"x.com: HTTP {resp.status}"
        except Exception:
            return None

    async def _check_via_nitter(self, username: str) -> tuple[Status, str] | None:
        for instance in NITTER_INSTANCES:
            url = f"https://{instance}/{username}"
            headers = {"User-Agent": TWITTER_UA}
            try:
                async with self._session.get(
                    url, headers=headers, timeout=8, allow_redirects=True
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        not_found = ["user not found", "doesn't exist", "404"]
                        if any(ind in text.lower() for ind in not_found):
                            return Status.AVAILABLE, f"nitter ({instance}): user not found"
                        return Status.TAKEN, f"nitter ({instance}): profile exists"
                    elif resp.status == 404:
                        return Status.AVAILABLE, f"nitter ({instance}): 404"
                    elif resp.status in (429, 403):
                        continue
                    continue
            except Exception:
                continue
        return None

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        result = await self._check_via_x(username)
        if result and result[0] != Status.UNKNOWN:
            return result

        nitter = await self._check_via_nitter(username)
        if nitter:
            return nitter

        return Status.UNKNOWN, "all methods blocked (use proxy)"
