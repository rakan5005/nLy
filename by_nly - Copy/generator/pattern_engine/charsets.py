"""Character sets for each platform and pattern expansion."""

import itertools

from ...models.enums import Platform

LETTERS = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"

CHARSETS = {
    Platform.SNAPCHAT: {
        "l": LETTERS,
        "d": DIGITS,
        "_": "_",
        ".": ".",
        "-": "-",
    },
    Platform.TELEGRAM: {
        "l": LETTERS,
        "d": DIGITS,
        "_": "_",
    },
    Platform.TIKTOK: {
        "l": LETTERS,
        "d": DIGITS,
        "_": "_",
        ".": ".",
    },
    Platform.TWITTER: {
        "l": LETTERS,
        "d": DIGITS,
        "_": "_",
    },
    Platform.TELLONYM: {
        "l": LETTERS,
        "d": DIGITS,
        "_": "_",
        ".": ".",
    },
    Platform.DISCORD: {
        "l": LETTERS,
        "d": DIGITS,
        "_": "_",
        ".": ".",
    },
}


def get_charset(platform: Platform) -> dict[str, str]:
    return CHARSETS.get(platform, CHARSETS[Platform.TELEGRAM])


def expand_pattern(template: str, charset: dict[str, str]) -> list[str]:
    """Expand a pattern template like 'll' or 'l_l' into all possible usernames."""
    import itertools

    pools = []
    for char in template:
        pool = charset.get(char)
        if pool is None:
            pools.append([char])
        else:
            pools.append(list(pool))

    return ["".join(combo) for combo in itertools.product(*pools)]


def expand_pattern_random(template: str, charset: dict[str, str], limit: int) -> list[str]:
    """Generate up to `limit` random usernames from the pattern space."""
    import random

    pools = []
    for char in template:
        pool = charset.get(char)
        if pool is None:
            pools.append([char])
        else:
            pools.append(list(pool))

    total = 1
    for p in pools:
        total *= len(p)

    if total <= limit * 2:
        # Small space: generate all and shuffle
        all_combos = ["".join(combo) for combo in itertools.product(*pools)]
        random.shuffle(all_combos)
        return all_combos

    # Large space: random sampling without building full list
    seen: set[str] = set()
    results: list[str] = []
    max_attempts = limit * 10
    attempts = 0
    while len(results) < limit and attempts < max_attempts:
        combo = "".join(random.choice(p) for p in pools)
        if combo not in seen:
            seen.add(combo)
            results.append(combo)
        attempts += 1
    return results


def pattern_size(template: str, charset: dict[str, str]) -> int:
    """Calculate how many usernames a pattern will generate."""
    size = 1
    for char in template:
        pool = charset.get(char)
        if pool is None:
            size *= 1
        else:
            size *= len(pool)
    return size
