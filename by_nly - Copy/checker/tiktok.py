"""TikTok availability checker via oembed API + urlebird mirror + web fallback."""

from .base import BaseChecker
from ..models.enums import Platform, Status

TIKTOK_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class TikTokChecker(BaseChecker):
    platform = Platform.TIKTOK

    def __init__(self, session):
        self._session = session

    async def _check_via_oembed(self, username: str) -> tuple[Status, str] | None:
        url = f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{username}"
        headers = {
            "User-Agent": TIKTOK_UA,
            "Accept": "application/json",
        }
        try:
            async with self._session.get(
                url, headers=headers, timeout=8, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if username.lower() in text.lower() or "author_name" in text:
                        return Status.TAKEN, "oembed: profile exists"
                    return None
                elif resp.status == 400:
                    return Status.AVAILABLE, "oembed: not found"
                return None
        except Exception:
            return None

    async def _check_via_urlebird(self, username: str) -> tuple[Status, str] | None:
        url = f"https://urlebird.com/user/{username}/"
        headers = {
            "User-Agent": TIKTOK_UA,
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            async with self._session.get(
                url, headers=headers, timeout=10, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    has_user = "followers" in text.lower() or "following" in text.lower()
                    if has_user:
                        return Status.TAKEN, "urlebird: profile exists"
                return None
        except Exception:
            return None

    async def _check_via_web(self, username: str) -> tuple[Status, str] | None:
        url = f"https://www.tiktok.com/@{username}"
        headers = {
            "User-Agent": TIKTOK_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            async with self._session.get(
                url, headers=headers, timeout=10, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    is_blocked = "captcha" in text.lower() or "verify you are human" in text.lower()
                    if is_blocked:
                        return None
                    has_og_title = '<meta property="og:title"' in text
                    not_found = "could not be found" in text or "doesn't exist" in text
                    if not_found or ('"statusCode":10221' in text and not has_og_title):
                        return Status.AVAILABLE, "web: not found"
                    if has_og_title:
                        return Status.TAKEN, "web: profile exists"
                    return None
                elif resp.status == 404:
                    return Status.AVAILABLE, "web: 404"
                return None
        except Exception:
            return None

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        oembed = await self._check_via_oembed(username)
        if oembed:
            return oembed

        urlebird = await self._check_via_urlebird(username)
        if urlebird:
            return urlebird

        web = await self._check_via_web(username)
        if web:
            return web

        return Status.UNKNOWN, "all methods blocked (use proxy)"
