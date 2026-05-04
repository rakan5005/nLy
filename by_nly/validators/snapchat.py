"""Snapchat username validator."""

import re
from .base import BaseValidator
from ..models.results import ValidationResult


class SnapchatValidator(BaseValidator):
    platform = "snapchat"

    # Must start with lowercase letter, then 3-15 chars from [a-z\-_.]
    # Total length: 4-16
    PATTERN = re.compile(r"^[a-z][a-z\-_.]{3,15}$")

    def validate(self, username: str) -> ValidationResult:
        username = self.normalize(username)
        if not self.PATTERN.match(username):
            return ValidationResult(
                False,
                "must start with a-z, contain only a-z - _ . and be 4-16 chars",
            )
        return ValidationResult(True)
