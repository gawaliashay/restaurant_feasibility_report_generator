"""
Full run: research → report → compile → save Markdown and JSON.

From the repo root:
    python -m src.pipeline_runners.pipeline
"""

import sys
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


def main() -> None:
    state = build_state()
    state = ResearchWorkflow().run(state)
    state = ReportWorkflow().run(state)
    markdown = ReportCompiler().compile(dict(state))
    files = export_report(markdown, dict(state))
    print("Wrote", files["md"])
    print("Wrote", files["json"])


if __name__ == "__main__":
    main()
