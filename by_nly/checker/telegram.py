"""Telegram availability checker via Telethon MTProto with t.me fallback."""

from .base import BaseChecker
from ..models.enums import Platform, Status


class TelegramChecker(BaseChecker):
    platform = Platform.TELEGRAM
    max_retries = 1

    def __init__(self, session):
        self._session = session
        self._client = None
        self._use_mtproto = False

    async def ensure_connected(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def _check_via_web(self, username: str) -> tuple[Status, str]:
        url = f"https://t.me/{username}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
        try:
            async with self._session.get(
                url, headers=headers, timeout=4, allow_redirects=True
            ) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if 'tgme_page_title' in text:
                        return Status.TAKEN, "telegram profile/page exists"
                    if 'joinchat' in resp.url.path or 'joinchat' in str(resp.url):
                        return Status.TAKEN, "telegram invite link"
                    return Status.AVAILABLE, "no profile"
                elif resp.status == 404:
                    return Status.AVAILABLE, "no profile"
                elif resp.status == 429:
                    return Status.RATE_LIMITED, "too many requests"
                return Status.UNKNOWN, f"HTTP {resp.status}"
        except Exception as e:
            return Status.UNKNOWN, str(e)[:200]

    async def _check_availability(self, username: str) -> tuple[Status, str]:
        return await self._check_via_web(username)
