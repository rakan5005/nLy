"""X (Twitter) availability checker — parallel bot UA + Nitter instances."""

import asyncio

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
    "nitter.nl",
    "nitter.it",
    "nitter.poast.org",
    "nitter.mint.lgbt",
    "nitter.kavin.rocks",
]


class TwitterChecker(BaseChecker):
    platform = Platform.TWITTER
    max_retries = 1

    def __init__(self, session):
        self._session = session

    async def _check_via_x(self, username: str) -> tuple[Status, str] | None:
        url = f"https://x.com/{username}"
        try:
            async with self._session.get(
                url, headers={"User-Agent": BOT_UA}, timeout=5, allow_redirects=True
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
                return None
        except Exception:
            return None

    async def _check_one_nitter(self, instance: str, username: str) -> tuple[Status, str] | None:
        url = f"https://{instance}/{username}"
        try:
            async with self._session.get(
                url, headers={"User-Agent": TWITTER_UA}, timeout=4, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if any(ind in text.lower() for ind in ["user not found", "doesn't exist", "404"]):
                        return Status.AVAILABLE, f"nitter ({instance}): not found"
                    return Status.TAKEN, f"nitter ({instance}): profile exists"
                elif resp.status == 404:
                    return Status.AVAILABLE, f"nitter ({instance}): 404"
                return None
        except Exception:
            return None

    async def _check_via_nitter(self, username: str) -> tuple[Status, str] | None:
        tasks = [asyncio.ensure_future(self._check_one_nitter(inst, username)) for inst in NITTER_INSTANCES]
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                try:
                    r = t.result()
                    if r:
                        for p in pending:
                            p.cancel()
                        return r
                except Exception:
                    pass
        finally:
            for p in pending:
                p.cancel()
        return None

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        x_task = asyncio.create_task(self._check_via_x(username))
        nitter_task = asyncio.create_task(self._check_via_nitter(username))

        x_result = await x_task
        if x_result and x_result[0] != Status.UNKNOWN:
            nitter_task.cancel()
            return x_result

        nitter_result = await nitter_task
        if nitter_result:
            return nitter_result

        return Status.UNKNOWN, "all methods blocked (use proxy)"
