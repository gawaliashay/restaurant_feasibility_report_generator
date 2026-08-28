"""Write compiled report to markdown and JSON."""

import json
import os
from datetime import datetime

from src.configuration.config_loader import config_loader


def export_report(report: str, state: dict) -> dict:
    reports_dir = (config_loader.get("paths.reports") or "reports").rstrip("/\\")
    os.makedirs(reports_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = os.path.join(reports_dir, f"report_{stamp}.md")
    json_path = os.path.join(reports_dir, f"report_{stamp}.json")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)

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
