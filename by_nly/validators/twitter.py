"""X (Twitter) username validator."""

import re
from .base import BaseValidator
from ..models.results import ValidationResult


class TwitterValidator(BaseValidator):
    platform = "twitter"

    # a-z, A-Z, 0-9, underscore only. 1-15 chars.
    PATTERN = re.compile(r"^[a-zA-Z0-9_]{1,15}$")

    def validate(self, username: str) -> ValidationResult:
        username = self.normalize(username)
        if not self.PATTERN.match(username):
            return ValidationResult(
                False,
                "must be 1-15 chars using a-z, 0-9 and underscore only",
            )
        return ValidationResult(True)
