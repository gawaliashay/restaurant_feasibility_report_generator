# src\workflow\report\report_exporter.py

"""
Report Exporter.
"""

import os
from datetime import datetime

from src.utils.report_exporter import save_json_generic, save_markdown_generic


def export_report(report: str, state: dict) -> dict:
    """Export report to MD and JSON using existing utilities."""
    os.makedirs("reports", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"reports/report_{timestamp}"

    md_path = f"{base}.md"
    save_markdown_generic(report, md_path)

    json_path = f"{base}.json"
    save_json_generic({
        "timestamp": datetime.now().isoformat(),
        "report": report,
        "concept": state.get("restaurant_concept"),
        "location": f"{state.get('local_area')}, {state.get('city')}",
    }, json_path)

    return {"md": md_path, "json": json_path}