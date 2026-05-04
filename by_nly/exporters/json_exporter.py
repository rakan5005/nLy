"""JSON exporter for check results."""

import json
from ..models.results import CheckResult


def export_json(results: list[CheckResult], filepath: str) -> str:
    data = []
    for r in results:
        data.append({
            "platform": r.platform.value,
            "username": r.username,
            "status": r.status.value,
            "reason": r.reason,
            "response_time_ms": int(r.response_time_ms),
            "timestamp": r.timestamp,
        })
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath
