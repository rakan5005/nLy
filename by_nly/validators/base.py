"""Base validator abstract class."""

from abc import ABC, abstractmethod
from ..models.results import ValidationResult


class BaseValidator(ABC):
    platform: str = "base"

    @abstractmethod
    def validate(self, username: str) -> ValidationResult:
        ...

    def normalize(self, username: str) -> str:
        return username.strip().lower()
