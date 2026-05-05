"""Per-platform rate limit configurations."""

import yaml
import os
from ..models.enums import Platform, SafeMode

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_LIMITS = {
    "default": {
        "requests_per_second": 5.0,
        "burst": 10,
    },
    "safe_mode": {
        "requests_per_second": 2.0,
        "burst": 5,
    },
    "strict_mode": {
        "requests_per_second": 0.5,
        "burst": 2,
    },
}


def load_platform_limits(platform: Platform) -> dict:
    """Load rate limits for a platform from its YAML config file."""
    config_path = os.path.join(_BASE_DIR, "config", "platforms", f"{platform.value}.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}

    defaults = DEFAULT_LIMITS["default"]
    result = {
        "default": {**defaults, **data.get("default", {})},
        "safe_mode": {**DEFAULT_LIMITS["safe_mode"], **data.get("safe_mode", {})},
        "strict_mode": {**DEFAULT_LIMITS["strict_mode"], **data.get("strict_mode", {})},
    }
    return result


def get_limit(
    platform: Platform,
    safe_mode: SafeMode | None = None,
) -> tuple[float, int]:
    """Get (rate, burst) for a platform and optional safe mode."""
    limits = load_platform_limits(platform)

    if safe_mode == SafeMode.STRICT_MODE:
        cfg = limits["strict_mode"]
    elif safe_mode == SafeMode.SAFE_MODE:
        cfg = limits["safe_mode"]
    else:
        cfg = limits["default"]

    return cfg["requests_per_second"], cfg["burst"]
