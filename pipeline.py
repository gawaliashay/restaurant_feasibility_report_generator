# pipeline.py

"""
Complete pipeline runner.
Executes both research and report workflows.
"""

from src.graph_states.workflow_states import WorkflowState
from src.workflow.research.research_workflow import ResearchWorkflow
from src.workflow.report.report_workflow import ReportWorkflow
from src.workflow.report.report_compiler import ReportCompiler
from src.workflow.report.report_exporter import export_report
from src.configuration.config_loader import config_loader



def build_state() -> WorkflowState:
    """Build initial state from config."""
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


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    """Run the complete pipeline."""
    print("🚀 Starting pipeline...")

    # Step 1: Build initial state
    state = build_state()

    # Step 2: Run Research Workflow
    print_section("📊 RESEARCH WORKFLOW")
    research = ResearchWorkflow()
    state = research.run(state)

    research_results = state.get("research_results", {})
    total_evidence = sum(
        len(r.get("evidence", [])) for r in research_results.values()
    )
    print(f"✅ Research completed: {total_evidence} evidence items")

    # Step 3: Run Report Workflow
    print_section("📄 REPORT WORKFLOW")
    report = ReportWorkflow()
    state = report.run(state)

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

    # Step 4: Export report
    print_section("💾 EXPORTING REPORT")
    report_content = final_report.get("report", "No report generated")
    files = export_report(report_content, dict(state))
    for fmt, path in files.items():
        print(f"✅ {fmt.upper()}: {path}")

    print_section("✅ PIPELINE COMPLETED")
    print(f"Total sections: {len(report_results)}")
    print(f"Total evidence: {total_evidence}")


if __name__ == "__main__":
    main()