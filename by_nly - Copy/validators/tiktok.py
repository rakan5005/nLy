"""TikTok username validator."""

import re
from .base import BaseValidator
from ..models.results import ValidationResult


class TikTokValidator(BaseValidator):
    platform = "tiktok"

    # a-z, A-Z, 0-9, underscore, period. 2-24 chars.
    # Cannot start or end with . or _
    PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.]{0,22}[a-zA-Z0-9]$|^[a-zA-Z0-9]$")

    def validate(self, username: str) -> ValidationResult:
        username = self.normalize(username)
        if len(username) < 2 or len(username) > 24:
            return ValidationResult(False, "must be 2-24 characters")
        if username.startswith(".") or username.startswith("_"):
            return ValidationResult(False, "cannot start with . or _")
        if username.endswith(".") or username.endswith("_"):
            return ValidationResult(False, "cannot end with . or _")
        if ".." in username:
            return ValidationResult(False, "consecutive dots not allowed")
        if "__" in username:
            return ValidationResult(False, "consecutive underscores not allowed")
        if not re.match(r"^[a-zA-Z0-9_.]+$", username):
            return ValidationResult(False, "only a-z, 0-9, _ and . allowed")
        return ValidationResult(True)
