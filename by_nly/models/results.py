"""Data models for check results, statistics, and batch outcomes."""

from dataclasses import dataclass, field
from datetime import datetime
from .enums import Platform, Status


@dataclass(slots=True)
class CheckResult:
    platform: Platform
    username: str
    status: Status
    reason: str = ""
    response_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_available(self) -> bool:
        return self.status == Status.AVAILABLE

    @property
    def is_taken(self) -> bool:
        return self.status == Status.TAKEN


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""


@dataclass
class Stats:
    total_generated: int = 0
    valid: int = 0
    invalid: int = 0
    checked: int = 0
    available: int = 0
    taken: int = 0
    unknown: int = 0
    rate_limited: int = 0
    checks_total_time_ms: float = 0.0
    start_time: float = 0.0

    @property
    def checks_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        return self.checked / elapsed if elapsed > 0 else 0.0

    @property
    def elapsed_seconds(self) -> float:
        from time import time
        return time() - self.start_time if self.start_time > 0 else 0.0

    def invalid_pct(self) -> float:
        return (self.invalid / self.total_generated * 100) if self.total_generated > 0 else 0.0

    def valid_pct(self) -> float:
        return (self.valid / self.total_generated * 100) if self.total_generated > 0 else 0.0

    def available_pct(self) -> float:
        return (self.available / self.checked * 100) if self.checked > 0 else 0.0

    def taken_pct(self) -> float:
        return (self.taken / self.checked * 100) if self.checked > 0 else 0.0
