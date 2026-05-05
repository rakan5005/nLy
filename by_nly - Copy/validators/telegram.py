"""Telegram username validator."""

import re
from .base import BaseValidator
from ..models.results import ValidationResult


class TelegramValidator(BaseValidator):
    platform = "telegram"

    # a-z, A-Z, 0-9, underscore only. 5-32 chars.
    PATTERN = re.compile(r"^[a-zA-Z0-9_]{5,32}$")

    def validate(self, username: str) -> ValidationResult:
        username = self.normalize(username)
        if not self.PATTERN.match(username):
            return ValidationResult(
                False,
                "must be 5-32 chars using a-z, 0-9 and underscore only",
            )
        return ValidationResult(True)
