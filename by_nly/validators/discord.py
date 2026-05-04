"""Discord username validator."""

import re
from .base import BaseValidator
from ..models.results import ValidationResult


class DiscordValidator(BaseValidator):
    platform = "discord"

    PATTERN = re.compile(r"^[a-zA-Z0-9_.]{2,32}$")

    def validate(self, username: str) -> ValidationResult:
        username = self.normalize(username)
        if not self.PATTERN.match(username):
            return ValidationResult(
                False,
                "must be 2-32 chars using a-z, 0-9, underscore and period only",
            )
        if username.startswith(".") or username.endswith("."):
            return ValidationResult(False, "cannot start or end with a period")
        if ".." in username:
            return ValidationResult(False, "cannot have consecutive periods")
        return ValidationResult(True)
