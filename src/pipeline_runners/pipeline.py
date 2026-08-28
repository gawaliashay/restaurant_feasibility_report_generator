"""Full run: research → report → compile → export. Saves evidence JSON for report-only reruns."""

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
    evidence_dir = (config_loader.get("paths.processed_evidence") or "processed_evidence").rstrip("/\\")
    os.makedirs(evidence_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(evidence_dir, f"research_results_{stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": datetime.now().isoformat(), "total_sections": len(results), "results": results},
            f,
            indent=2,
            default=str,
        )
    return path


def main() -> None:
    state = build_state()
    state = ResearchWorkflow().run(state)
    print("Wrote", save_research_results(state.get("research_results", {})))

    state = ReportWorkflow().run(state)
    files = export_report(ReportCompiler().compile(dict(state)), dict(state))
    state["export_paths"] = files
    print("Wrote", files["md"])
    print("Wrote", files["json"])


if __name__ == "__main__":
    main()
