"""
Full run: research → report → compile → save Markdown and JSON.

Also saves research evidence JSON so report_pipeline_runner can reuse it.

From the repo root:
    python -m src.pipeline_runners.pipeline
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.workflow.research.research_workflow import ResearchWorkflow
from src.workflow.report.report_workflow import ReportWorkflow
from src.workflow.report.report_compiler import ReportCompiler
from src.workflow.report.report_exporter import export_report


def build_state() -> WorkflowState:
    business = config_loader.get("business_case.default", {})
    location = business.get("location", {})
    return {
        "restaurant_concept": business.get("restaurant_concept"),
        "investment": business.get("investment"),
        "target_demographic": business.get("target_demographic"),
        "special_note": business.get("special_note"),
        "society": location.get("society"),
        "local_area": location.get("local_area"),
        "city": location.get("city"),
        "state": location.get("state"),
        "country": location.get("country"),
        "pincode": location.get("pincode"),
        "research_results": {},
        "section_reports": {},
        "errors": [],
    }


def save_research_results(results: dict) -> str:
    """Write evidence packet for later report-only runs."""
    os.makedirs("processed_evidence", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"processed_evidence/research_results_{stamp}.json"
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total_sections": len(results),
        "results": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return path


def main() -> None:
    state = build_state()
    state = ResearchWorkflow().run(state)
    evidence_path = save_research_results(state.get("research_results", {}))
    print("Wrote", evidence_path)

    state = ReportWorkflow().run(state)
    markdown = ReportCompiler().compile(dict(state))
    files = export_report(markdown, dict(state))
    print("Wrote", files["md"])
    print("Wrote", files["json"])


if __name__ == "__main__":
    main()
