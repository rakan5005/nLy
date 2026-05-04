"""Tellonym username validator."""

import re
from .base import BaseValidator
from ..models.results import ValidationResult


class TellonymValidator(BaseValidator):
    platform = "tellonym"

    # a-z, A-Z, 0-9, underscore, period. 1-30 chars.
    PATTERN = re.compile(r"^[a-zA-Z0-9_.]{1,30}$")

    def validate(self, username: str) -> ValidationResult:
        username = self.normalize(username)
        if not self.PATTERN.match(username):
            return ValidationResult(
                False,
                "must be 1-30 chars using a-z, 0-9, _ and .",
            )
        return ValidationResult(True)
