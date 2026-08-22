"""
Unified pipeline runner - runs research + report workflows together.

USAGE:
    # Run from project root
    python -m src.pipeline_runners.pipeline

    # Run from src/pipeline_runners directory
    cd src/pipeline_runners
    python pipeline.py

    # Skip research (use existing results from previous run)
    python -m src.pipeline_runners.pipeline --skip-research

    # Load research from specific file
    python -m src.pipeline_runners.pipeline --research-file reports/processed_evidence/research_results_20260822_022150.json

    # Load latest research results
    python -m src.pipeline_runners.pipeline --latest-research
"""

import json
import argparse
import sys
import glob
import os
from pathlib import Path

# Add project root to path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.workflow.research.research_workflow import ResearchWorkflow
from src.workflow.report.report_workflow import ReportWorkflow
from src.workflow.report.report_compiler import ReportCompiler
from src.workflow.report.report_exporter import export_report


# ============================================================
# HELPERS
# ============================================================

def get_latest_research_file() -> str:
    """Get the most recent research results file."""
    files = glob.glob("reports/processed_evidence/research_results_*.json")
    if not files:
        return None
    return max(files, key=os.path.getctime)


def build_state() -> WorkflowState:
    """Build workflow state from config."""
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


def load_research_results(filepath: str) -> dict:
    """Load research results from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("results", {})


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():
    """Run the complete pipeline."""
    parser = argparse.ArgumentParser(description="Run full feasibility pipeline")
    parser.add_argument(
        "--skip-research",
        action="store_true",
        help="Skip research phase (use existing results)"
    )
    parser.add_argument(
        "--research-file",
        type=str,
        help="Load research results from JSON file"
    )
    parser.add_argument(
        "--latest-research",
        action="store_true",
        help="Use the latest research results file"
    )
    args = parser.parse_args()

    print("🚀 Starting pipeline...")

    state = build_state()

    # Step 1: Research
    if args.skip_research:
        print_section("📊 SKIPPING RESEARCH")
        print("⚠️  Using existing state (no research data)")
    elif args.research_file:
        print_section(f"📊 LOADING RESEARCH FROM: {args.research_file}")
        state["research_results"] = load_research_results(args.research_file)
        total_evidence = sum(
            len(r.get("evidence", [])) for r in state["research_results"].values()
        )
        print(f"✅ Loaded research: {total_evidence} evidence items")
    elif args.latest_research:
        filepath = get_latest_research_file()
        if filepath:
            print_section(f"📊 LOADING LATEST RESEARCH: {filepath}")
            state["research_results"] = load_research_results(filepath)
            total_evidence = sum(
                len(r.get("evidence", [])) for r in state["research_results"].values()
            )
            print(f"✅ Loaded research: {total_evidence} evidence items")
        else:
            print_section("📊 RUNNING RESEARCH (no saved results found)")
            research = ResearchWorkflow()
            state = research.run(state)
            total_evidence = sum(
                len(r.get("evidence", [])) for r in state["research_results"].values()
            )
            print(f"✅ Research completed: {total_evidence} evidence items")
    else:
        print_section("📊 RESEARCH WORKFLOW")
        research = ResearchWorkflow()
        state = research.run(state)

        research_results = state.get("research_results", {})
        total_evidence = sum(
            len(r.get("evidence", [])) for r in research_results.values()
        )
        print(f"✅ Research completed: {total_evidence} evidence items")

    # Step 2: Report
    print_section("📄 REPORT WORKFLOW")
    report = ReportWorkflow()
    state = report.run(state)

    # Step 3: Compile
    compiler = ReportCompiler()
    final_report = compiler.compile(dict(state))
    state["section_reports"]["final_compilation"] = {
        "section": "final_compilation",
        "status": "success",
        "report": final_report,
    }

    report_results = state.get("section_reports", {})
    final_report = report_results.get("final_compilation", {})
    print(f"✅ Report completed: {len(report_results)} sections")

    # Step 4: Export
    print_section("💾 EXPORTING REPORT")
    report_content = final_report.get("report", "No report generated")
    files = export_report(report_content, dict(state))
    for fmt, path in files.items():
        print(f"✅ {fmt.upper()}: {path}")

    print_section("✅ PIPELINE COMPLETED")
    print(f"Total sections: {len(report_results)}")
    print(f"Total evidence: {total_evidence if 'total_evidence' in locals() else 'N/A'}")


if __name__ == "__main__":
    main()