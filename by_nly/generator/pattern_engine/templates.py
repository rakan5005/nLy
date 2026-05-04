"""Built-in pattern template sets (semi2, semi3, quad, full)."""

PATTERN_SETS = {
    "semi2": [
        "ll", "ld", "dl",
        "l_l", "l.l",
        "lld", "dll",
    ],
    "semi3": [
        "lll", "lld", "ldl", "dll",
        "llld", "dlll", "ll_l", "ll.l",
        "l_ll", "l.ll", "ll_d", "ld_l",
        "ldl", "dl_l",
    ],
    "quad": [
        "llll", "llld", "ldll", "dlll", "ldld",
        "llld", "dllld", "lldd", "ldll",
        "lll.l", "ll.ll", "l.l.l.l",
    ],
    "full": [],  # resolved recursively below
}

# "full" is the union of all others
PATTERN_SETS["full"] = PATTERN_SETS["semi2"] + PATTERN_SETS["semi3"] + PATTERN_SETS["quad"]


def get_patterns(pattern_type: str) -> list[str]:
    key = pattern_type.lower()
    if key not in PATTERN_SETS:
        valid = ", ".join(PATTERN_SETS.keys())
        raise ValueError(f"Unknown pattern type '{pattern_type}'. Valid: {valid}")
    return PATTERN_SETS[key]


def list_pattern_types() -> list[str]:
    return list(PATTERN_SETS.keys())
