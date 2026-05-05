"""Snapchat availability checker via profile + Bitmoji API fallback."""

from .base import BaseChecker
from ..models.enums import Platform, Status

SNAPCHAT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class SnapchatChecker(BaseChecker):
    platform = Platform.SNAPCHAT

    def __init__(self, session):
        self._session = session

    async def _check_via_bitmoji(self, username: str) -> tuple[Status, str] | None:
        """Check via Bitmoji API (public, no auth)."""
        url = f"https://bitmoji.api.snapchat.com/api/user/find?username={username}"
        headers = {
            "User-Agent": SNAPCHAT_UA,
            "Accept": "application/json",
        }
        try:
            async with self._session.get(url, headers=headers, timeout=8) as resp:
                if resp.status == 200:
                    return Status.TAKEN, "bitmoji: user found"
                elif resp.status == 404:
                    return Status.AVAILABLE, "bitmoji: no user"
        except Exception:
            return None

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        url = f"https://www.snapchat.com/add/{username}"
        headers = {"User-Agent": SNAPCHAT_UA}
        try:
            async with self._session.get(
                url, headers=headers, timeout=10, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    not_found = [
                        "could not be found",
                        "this content doesn't exist",
                        "Sorry, we couldn't find",
                        "doesn't exist",
                    ]
                    if any(ind in text for ind in not_found):
                        return Status.AVAILABLE, "web: user not found"
                    return Status.TAKEN, "web: profile exists"
                elif resp.status == 404:
                    return Status.AVAILABLE, "web: 404"
                elif resp.status in (403, 429):
                    bitmoji = await self._check_via_bitmoji(username)
                    if bitmoji:
                        return bitmoji
                    return Status.UNKNOWN, "Cloudflare blocked (use --proxy)"
                return Status.UNKNOWN, f"HTTP {resp.status}"
        except Exception as e:
            bitmoji = await self._check_via_bitmoji(username)
            if bitmoji:
                return bitmoji
            return Status.UNKNOWN, str(e)[:200]
