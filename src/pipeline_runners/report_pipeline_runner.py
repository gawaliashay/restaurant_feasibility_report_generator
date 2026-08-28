"""Report + compile from saved research JSON (no Maps / Tavily)."""

import glob
import json
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.configuration.config_loader import config_loader
from src.pipeline_runners.pipeline import build_state
from src.workflow.report.report_compiler import ReportCompiler
from src.workflow.report.report_exporter import export_report
from src.workflow.report.report_workflow import ReportWorkflow


def main() -> None:
    evidence_dir = (config_loader.get("paths.processed_evidence") or "processed_evidence").rstrip("/\\")
    files = glob.glob(os.path.join(evidence_dir, "research_results_*.json"))
    if not files:
        print("No saved research. Run: python -m src.pipeline_runners.research_pipeline_runner")
        raise SystemExit(1)

    path = max(files, key=os.path.getctime)
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)

    state = build_state()
    state["research_results"] = saved.get("results", {})
    print("Loaded", path)

    state = ReportWorkflow().run(state)
    files = export_report(ReportCompiler().compile(dict(state)), dict(state))
    state["export_paths"] = files
    print("Wrote", files["md"])
    print("Wrote", files["json"])


if __name__ == "__main__":
    main()
