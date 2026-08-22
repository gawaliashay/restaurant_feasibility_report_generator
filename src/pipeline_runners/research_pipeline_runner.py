"""
Research pipeline runner - standalone entry point for evidence collection.

USAGE:
    # Run from project root
    python -m src.pipeline_runners.research_pipeline_runner

    # Or from src/pipeline_runners directory
    cd src/pipeline_runners
    python research_pipeline_runner.py

    # With save option
    python -m src.pipeline_runners.research_pipeline_runner --save

    # Run specific section only
    python -m src.pipeline_runners.research_pipeline_runner --section market_analysis
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.research.research_workflow import ResearchWorkflow


# ============================================================
# HELPERS
# ============================================================

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
        "errors": [],
    }


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_evidence(item: dict, idx: int) -> None:
    """Print a single evidence item."""
    source = item.get("source", "unknown")
    title = item.get("title", "")
    text = item.get("content", item.get("text", ""))

    if title:
        print(f"  {idx+1}. {source}: {title}")
    elif text:
        print(f"  {idx+1}. {source}: {text[:80]}...")
    else:
        print(f"  {idx+1}. {source}: No content")


def print_section_result(section_name: str, result: dict) -> None:
    """Print a section result."""
    print_header(section_name.replace("_", " ").title())
    print(f"Status: {result.get('status')}")

    evidence = result.get("evidence", [])
    print(f"Evidence: {len(evidence)}")

    if result.get("error"):
        print(f"Error: {result.get('error')}")

    for idx, item in enumerate(evidence[:5]):
        print_evidence(item, idx)

    if len(evidence) > 5:
        print(f"  ... and {len(evidence) - 5} more")


def print_summary(results: dict) -> None:
    """Print summary statistics."""
    print_header("SUMMARY")
    print(f"Total sections: {len(results)}")
    print(f"Successful: {sum(1 for r in results.values() if r.get('status') == 'success')}")
    print(f"Total evidence: {sum(len(r.get('evidence', [])) for r in results.values())}")
    print("=" * 60)


def save_results(results: dict) -> str:
    """Save results to JSON file."""
    import os
    
    os.makedirs("reports/processed_evidence/", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/processed_evidence/research_results_{timestamp}.json"
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_sections": len(results),
        "results": results,
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    
    return filename


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Run the research workflow."""
    parser = argparse.ArgumentParser(description="Run research evidence collection")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to file"
    )
    parser.add_argument(
        "--section",
        type=str,
        help="Run specific section only (optional)"
    )
    args = parser.parse_args()

    try:
        state = build_state()
        print("📊 Using config data")

        # Run workflow
        workflow = ResearchWorkflow()
        result = workflow.run(state)

        research_results = result.get("research_results", {})

        # Filter if specific section requested
        if args.section:
            if args.section in research_results:
                research_results = {args.section: research_results[args.section]}
            else:
                print(f"⚠️ Section '{args.section}' not found")

        print_header("RESEARCH WORKFLOW COMPLETED")

        for section_name, section_result in research_results.items():
            print_section_result(section_name, section_result)

        print_summary(research_results)

        if args.save:
            print_header("SAVING RESULTS")
            print(f"✅ Saved to: {save_results(research_results)}")
            print("=" * 60)

    except Exception as e:
        logger.exception("Workflow failed")
        print(f"\n❌ FAILED: {str(e)}")
        raise


if __name__ == "__main__":
    main()