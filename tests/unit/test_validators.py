"""Tests for username validators across all platforms."""

import pytest
from by_nly.models.enums import Platform
from by_nly.validators import get_validator
from by_nly.validators.snapchat import SnapchatValidator
from by_nly.validators.telegram import TelegramValidator
from by_nly.validators.tiktok import TikTokValidator
from by_nly.validators.twitter import TwitterValidator
from by_nly.validators.tellonym import TellonymValidator


class TestSnapchatValidator:
    def test_valid_usernames(self):
        v = SnapchatValidator()
        assert v.validate("nlyx").is_valid
        assert v.validate("test_user").is_valid
        assert v.validate("user-name").is_valid
        assert v.validate("x.zy").is_valid

    def test_invalid_too_short(self):
        v = SnapchatValidator()
        assert not v.validate("ab").is_valid  # 2 chars, min 4

    def test_invalid_start_with_number(self):
        v = SnapchatValidator()
        assert not v.validate("1user").is_valid

    def test_invalid_special_chars(self):
        v = SnapchatValidator()
        assert not v.validate("user@name").is_valid
        assert not v.validate("hello world").is_valid

    def test_normalize_lowercase(self):
        v = SnapchatValidator()
        assert v.validate("NLYX").is_valid  # normalize applies lowercase


class TestTelegramValidator:
    def test_valid_usernames(self):
        v = TelegramValidator()
        assert v.validate("nlyx12").is_valid
        assert v.validate("abcde").is_valid  # exactly 5
        assert v.validate("test_user").is_valid

    def test_invalid_too_short(self):
        v = TelegramValidator()
        assert not v.validate("nlyx").is_valid  # 4 chars, min 5

    def test_invalid_dot(self):
        v = TelegramValidator()
        assert not v.validate("test.user").is_valid  # dots not allowed


class TestTikTokValidator:
    def test_valid_usernames(self):
        v = TikTokValidator()
        assert v.validate("nlyx").is_valid
        assert v.validate("test.user").is_valid
        assert v.validate("user_123").is_valid
        assert v.validate("x1").is_valid  # 2 chars

    def test_invalid_starts_with_dot(self):
        v = TikTokValidator()
        assert not v.validate(".user").is_valid

    def test_invalid_ends_with_dot(self):
        v = TikTokValidator()
        assert not v.validate("user.").is_valid

    def test_invalid_consecutive_dots(self):
        v = TikTokValidator()
        assert not v.validate("n..ly").is_valid

    def test_invalid_consecutive_underscores(self):
        v = TikTokValidator()
        assert not v.validate("n__ly").is_valid


class TestTwitterValidator:
    def test_valid_usernames(self):
        v = TwitterValidator()
        assert v.validate("nlyx").is_valid
        assert v.validate("test_user").is_valid
        assert v.validate("x").is_valid  # 1 char

    def test_invalid_too_long(self):
        v = TwitterValidator()
        assert not v.validate("a" * 16).is_valid  # max 15

    def test_invalid_dot(self):
        v = TwitterValidator()
        assert not v.validate("test.user").is_valid


class TestTellonymValidator:
    def test_valid_usernames(self):
        v = TellonymValidator()
        assert v.validate("nlyx").is_valid
        assert v.validate("test.user").is_valid
        assert v.validate("x").is_valid

    def test_invalid_too_long(self):
        v = TellonymValidator()
        assert not v.validate("a" * 31).is_valid  # max 30


class TestValidatorFactory:
    def test_get_validator(self):
        for p in Platform:
            v = get_validator(p)
            assert v is not None
            assert v.platform != "base"

    def test_invalid_platform_raises(self):
        with pytest.raises(ValueError):
            get_validator("invalid_platform")
