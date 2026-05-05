"""Generator Engine - orchestrates username generation, validation, and deduplication."""

import random

from ..models.enums import Platform
from ..models.results import Stats
from ..validators import get_validator
from .pattern_engine import (
    get_charset,
    expand_pattern,
    expand_pattern_random,
    get_patterns,
    custom_pattern_to_template,
)


class Generator:
    def __init__(self, platform: Platform, pattern: str, limit: int | None = None):
        self.platform = platform
        self.pattern_input = pattern
        self.limit = limit
        self.charset = get_charset(platform)
        self.validator = get_validator(platform)
        self.stats = Stats()

    def generate(self) -> list[str]:
        templates = self._resolve_templates()
        templates = self._filter_short_templates(templates)
        if not templates:
            return []
        random.shuffle(templates)
        seen: set[str] = set()
        valid_usernames: list[str] = []

        if self.limit:
            per_template = max(1, self.limit // len(templates))
        else:
            per_template = None

        for tmpl in templates:
            if self.limit and len(valid_usernames) >= self.limit:
                break

            if per_template:
                remaining = min(per_template, self.limit - len(valid_usernames))
                names = expand_pattern_random(tmpl, self.charset, remaining)
            else:
                names = expand_pattern(tmpl, self.charset)

            for name in names:
                if self.limit and len(valid_usernames) >= self.limit:
                    break
                self.stats.total_generated += 1
                self._filter_one(name, seen, valid_usernames)

        if self.limit and len(valid_usernames) > self.limit:
            valid_usernames = valid_usernames[: self.limit]

        random.shuffle(valid_usernames)
        return valid_usernames

    def _min_template_length(self) -> int:
        lengths = {
            Platform.TELEGRAM: 5,
            Platform.TWITTER: 4,
        }
        return lengths.get(self.platform, 1)

    def _filter_short_templates(self, templates: list[str]) -> list[str]:
        min_len = self._min_template_length()
        if min_len <= 1:
            return templates
        filtered = [t for t in templates if len(t) >= min_len]
        return filtered

    def _resolve_templates(self) -> list[str]:
        pattern = self.pattern_input.strip()
        if pattern.startswith("custom:"):
            return [custom_pattern_to_template(pattern)]

        try:
            return get_patterns(pattern)
        except ValueError:
            return [pattern]

    def _filter_one(
        self,
        username: str,
        seen: set[str],
        out: list[str],
    ) -> None:
        if username in seen:
            return
        seen.add(username)

        result = self.validator.validate(username)
        if result.is_valid:
            out.append(username)
            self.stats.valid += 1
        else:
            self.stats.invalid += 1
