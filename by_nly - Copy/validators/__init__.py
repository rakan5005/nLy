"""Validator factory - returns the correct validator for a platform."""

from ..models.enums import Platform
from .base import BaseValidator
from .snapchat import SnapchatValidator
from .telegram import TelegramValidator
from .tiktok import TikTokValidator
from .twitter import TwitterValidator
from .tellonym import TellonymValidator
from .discord import DiscordValidator

_VALIDATORS = {
    Platform.SNAPCHAT: SnapchatValidator,
    Platform.TELEGRAM: TelegramValidator,
    Platform.TIKTOK: TikTokValidator,
    Platform.TWITTER: TwitterValidator,
    Platform.TELLONYM: TellonymValidator,
    Platform.DISCORD: DiscordValidator,
}


def get_validator(platform: Platform) -> BaseValidator:
    cls = _VALIDATORS.get(platform)
    if cls is None:
        raise ValueError(f"No validator registered for platform: {platform}")
    return cls()
