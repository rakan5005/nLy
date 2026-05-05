"""TXT exporter for check results - one username per line, grouped by status."""

import os
from ..models.results import CheckResult, Status


def export_txt(results: list[CheckResult], directory: str) -> dict[str, str]:
    os.makedirs(directory, exist_ok=True)
    files = {}

    grouped: dict[Status, list[str]] = {s: [] for s in Status}
    for r in results:
        grouped[r.status].append(r.username)

    for status, names in grouped.items():
        if not names:
            continue
        filepath = os.path.join(directory, f"{status.value}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(names))
        files[status.value] = filepath

    return files
