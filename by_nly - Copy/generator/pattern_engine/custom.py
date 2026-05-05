"""Custom pattern parser for user-defined templates like custom:ll.l or custom:ld_ld."""

import re

TOKEN_MAP = {
    "l": "l",  # lowercase letter
    "d": "d",  # digit
    "_": "_",  # underscore (literal)
    ".": ".",  # dot (literal)
    "1": "d",  # digit alias for readability
    "2": "d",
    "3": "d",
    "4": "d",
    "5": "d",
    "6": "d",
    "7": "d",
    "8": "d",
    "9": "d",
    "0": "d",
}


def parse_custom_pattern(template: str) -> list[str]:
    """Parse a custom pattern string into individual tokens.

    Examples:
        custom:ll.l    -> ["l", "l", ".", "l"]
        custom:l_ll1   -> ["l", "_", "l", "l", "d"]
        custom:l1l2    -> ["l", "d", "l", "d"]
    """
    clean = template.strip()
    if clean.startswith("custom:"):
        clean = clean[7:]

    clean = re.sub(r"\s+", "", clean)

    tokens = []
    for ch in clean:
        mapped = TOKEN_MAP.get(ch)
        if mapped is None:
            raise ValueError(
                f"Invalid character '{ch}' in custom pattern '{template}'. "
                f"Allowed: l, d, _, ., 0-9"
            )
        tokens.append(mapped)

    if not tokens:
        raise ValueError(f"Empty pattern: '{template}'")

    return tokens


def custom_pattern_to_template(template: str) -> str:
    """Convert custom pattern to internal template format."""
    tokens = parse_custom_pattern(template)
    return "".join(tokens)
