"""Enums for platforms, statuses, pattern types, and safe modes."""

from enum import StrEnum


class Platform(StrEnum):
    SNAPCHAT = "snapchat"
    TELEGRAM = "telegram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    TELLONYM = "tellonym"
    DISCORD = "discord"

    @classmethod
    def display_name(cls, platform: "Platform") -> str:
        names = {
            cls.SNAPCHAT: "Snapchat",
            cls.TELEGRAM: "Telegram",
            cls.TIKTOK: "TikTok",
            cls.TWITTER: "X (Twitter)",
            cls.TELLONYM: "Tellonym",
            cls.DISCORD: "Discord",
        }
        return names.get(platform, platform.value)

    @classmethod
    def safety_level(cls, platform: "Platform") -> str:
        levels = {
            cls.TELLONYM: "safe",
            cls.TELEGRAM: "safe",
            cls.DISCORD: "safe",
            cls.SNAPCHAT: "danger",
            cls.TIKTOK: "danger",
            cls.TWITTER: "danger",
        }
        return levels.get(platform, "unknown")

    @classmethod
    def safety_warning(cls, platform: "Platform") -> str:
        warnings = {
            cls.SNAPCHAT: "Snapchat uses Cloudflare anti-bot - your IP may be temporarily blocked after ~100 checks",
            cls.TIKTOK: "TikTok uses Akamai bot detection - your IP may be rate limited",
            cls.TWITTER: "X has the strictest IP blocking - use only with small batches",
            cls.DISCORD: "Discord uses hCaptcha on registration - rate limit after ~200 checks. Use --proxy if blocked.",
        }
        return warnings.get(platform, "")

    @classmethod
    def safe_platforms(cls) -> list["Platform"]:
        return [cls.TELLONYM, cls.TELEGRAM, cls.DISCORD]

    @classmethod
    def danger_platforms(cls) -> list["Platform"]:
        return [cls.SNAPCHAT, cls.TIKTOK, cls.TWITTER]


class Status(StrEnum):
    AVAILABLE = "available"
    TAKEN = "taken"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    RATE_LIMITED = "rate_limited"


class PatternType(StrEnum):
    SEMI2 = "semi2"
    SEMI3 = "semi3"
    QUAD = "quad"
    CUSTOM = "custom"
    FULL = "full"


class SafeMode(StrEnum):
    VALIDATE_ONLY = "validate-only"
    CHECK_ONLY = "check-only"
    GENERATE_AND_CHECK = "generate-and-check"
    SAFE_MODE = "safe-mode"
    STRICT_MODE = "strict-mode"
