"""Availability checker factory."""

from ..models.enums import Platform
from .base import BaseChecker
from .snapchat import SnapchatChecker
from .telegram import TelegramChecker
from .tiktok import TikTokChecker
from .twitter import TwitterChecker
from .tellonym import TellonymChecker
from .discord import DiscordChecker


def get_checker(platform: Platform, session, proxy_manager=None) -> BaseChecker:
    checkers = {
        Platform.SNAPCHAT: SnapchatChecker,
        Platform.TELEGRAM: TelegramChecker,
        Platform.TIKTOK: TikTokChecker,
        Platform.TWITTER: TwitterChecker,
        Platform.TELLONYM: TellonymChecker,
        Platform.DISCORD: DiscordChecker,
    }
    cls = checkers.get(platform)
    if cls is None:
        raise ValueError(f"No checker registered for platform: {platform}")
    if platform == Platform.DISCORD:
        return cls(session, proxy_manager=proxy_manager)
    return cls(session)
