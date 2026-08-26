"""
Stage check: report + compile from saved research JSON (no Maps / Tavily).

Needs a file under processed_evidence/ (run research_pipeline_runner or pipeline first).

From the repo root:
    python -m src.pipeline_runners.report_pipeline_runner
"""

import glob
import json
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.pipeline_runners.pipeline import build_state
from src.workflow.report.report_compiler import ReportCompiler
from src.workflow.report.report_exporter import export_report
from src.workflow.report.report_workflow import ReportWorkflow


def latest_research_path() -> str | None:
    files = glob.glob("processed_evidence/research_results_*.json")
    if not files:
        return None
    return max(files, key=os.path.getctime)


def main() -> None:
    path = latest_research_path()
    if not path:
        print("No saved research. Run: python -m src.pipeline_runners.research_pipeline_runner")
        raise SystemExit(1)

    with open(path, encoding="utf-8") as f:
        saved = json.load(f)

    state = build_state()
    state["research_results"] = saved.get("results", {})
    print("Loaded", path)

    state = ReportWorkflow().run(state)
    markdown = ReportCompiler().compile(dict(state))
    files = export_report(markdown, dict(state))
    print("Wrote", files["md"])
    print("Wrote", files["json"])


if __name__ == "__main__":
    main()
