# src/workflow/report/report_exporter.py

"""
Write the compiled report to markdown and JSON.
"""

import json
import os
from datetime import datetime


def export_report(report: str, state: dict) -> dict:
    """Export report to MD and JSON. Returns {md: path, json: path}."""
    os.makedirs("reports", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"reports/report_{timestamp}"

    md_path = f"{base}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)

    json_path = f"{base}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "report": report,
                "concept": state.get("restaurant_concept"),
                "location": f"{state.get('local_area')}, {state.get('city')}",
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return {"md": md_path, "json": json_path}