"""CSV exporter for check results."""

import csv
from ..models.results import CheckResult


def export_csv(results: list[CheckResult], filepath: str) -> str:
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["platform", "username", "status", "reason", "response_time_ms", "timestamp"])
        for r in results:
            writer.writerow([
                r.platform.value,
                r.username,
                r.status.value,
                r.reason,
                f"{r.response_time_ms:.0f}",
                r.timestamp,
            ])
    return filepath
