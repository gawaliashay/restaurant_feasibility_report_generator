"""
Report pipeline runner - standalone entry point for report generation.

USAGE:
    # Run from project root
    python -m src.pipeline_runners.report_pipeline_runner

    # Run from src/pipeline_runners directory
    cd src/pipeline_runners
    python report_pipeline_runner.py

    # Run report from existing research results
    python -m src.pipeline_runners.report_pipeline_runner --research-file reports/processed_evidence/research_results_20260822_022150.json

    # Skip exporting (just print to console)
    python -m src.pipeline_runners.report_pipeline_runner --no-export

    # Run specific report section only
    python -m src.pipeline_runners.report_pipeline_runner --section market_report

    # Load research from default location (latest)
    python -m src.pipeline_runners.report_pipeline_runner --latest-research
"""

import json
import argparse
import sys
import os
import glob
from pathlib import Path
from datetime import datetime

# Add project root to path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
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


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_section_report(section_name: str, result: dict) -> None:
    """Print a report section result."""
    print_header(section_name.replace("_", " ").title())
    print(f"Status: {result.get('status')}")
    
    report = result.get("report", "")
    if report:
        print(f"Report length: {len(report)} characters")
        print("\nPreview:")
        preview = report[:500]
        if len(report) > 500:
            preview += "..."
        print(preview)
    
    if result.get("error"):
        print(f"Error: {result.get('error')}")


def print_summary(results: dict) -> None:
    """Print summary statistics."""
    print_header("SUMMARY")
    successful = sum(1 for r in results.values() if r.get('status') == 'success')
    print(f"Total sections: {len(results)}")
    print(f"Successful: {successful}")
    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Run the report workflow."""
    parser = argparse.ArgumentParser(description="Run report generation")
    parser.add_argument(
        "--research-file",
        type=str,
        help="Path to research results JSON file (skips research phase)"
    )
    parser.add_argument(
        "--latest-research",
        action="store_true",
        help="Use the latest research results file"
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip exporting to files"
    )
    parser.add_argument(
        "--section",
        type=str,
        help="Run specific report section only"
    )
    args = parser.parse_args()

    try:
        # Build state
        if args.research_file:
            print(f"📊 Loading research results from: {args.research_file}")
            research_results = load_research_results(args.research_file)
            state = build_state()
            state["research_results"] = research_results
        elif args.latest_research:
            filepath = get_latest_research_file()
            if filepath:
                print(f"📊 Loading latest research results from: {filepath}")
                research_results = load_research_results(filepath)
                state = build_state()
                state["research_results"] = research_results
            else:
                print("⚠️ No research results found. Running research first...")
                from src.pipeline_runners.research_pipeline_runner import build_state, ResearchWorkflow
                state = build_state()
                research = ResearchWorkflow()
                state = research.run(state)
        else:
            # Run research first
            print("📊 Running research workflow first...")
            from src.pipeline_runners.research_pipeline_runner import build_state, ResearchWorkflow
            
            state = build_state()
            research = ResearchWorkflow()
            state = research.run(state)

        # Run report workflow
        print_header("RUNNING REPORT WORKFLOW")
        workflow = ReportWorkflow()
        result = workflow.run(state)

        report_results = result.get("section_reports", {})

        # Filter if specific section requested
        if args.section:
            if args.section in report_results:
                report_results = {args.section: report_results[args.section]}
            else:
                print(f"⚠️ Section '{args.section}' not found")

        print_header("REPORT WORKFLOW COMPLETED")

        for section_name, section_result in report_results.items():
            print_section_report(section_name, section_result)

        print_summary(report_results)

        # Compile final report
        print_header("COMPILING FINAL REPORT")
        compiler = ReportCompiler()
        final_report = compiler.compile(dict(state))
        print(f"✅ Final report length: {len(final_report)} characters")
        print("\nPreview:")
        print(final_report[:500] + "...")

        # Export
        if not args.no_export:
            print_header("EXPORTING REPORT")
            files = export_report(final_report, dict(state))
            for fmt, path in files.items():
                print(f"✅ {fmt.upper()}: {path}")
            print("=" * 60)

    except Exception as e:
        logger.exception("Report workflow failed")
        print(f"\n❌ FAILED: {str(e)}")
        raise


if __name__ == "__main__":
    main()