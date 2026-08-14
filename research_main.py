"""
Application entry point for research workflow.
"""

from src.graph_states.workflow_states import WorkflowState
from src.workflow.research.research_workflow import ResearchWorkflow
from src.logging_exception.logging.logger import logger
from src.configuration.config_loader import config_loader


def build_state_from_config() -> WorkflowState:
    """
    Build WorkflowState entirely from configuration.
    No hardcoding - everything comes from config.
    """
    business_case = config_loader.get("business_case.default", {})
    location = business_case.get("location", {})
    
    # Build state from config with no hardcoded defaults
    state: WorkflowState = {
        "restaurant_concept": business_case.get("restaurant_concept"),
        "investment": business_case.get("investment"),
        "target_demographic": business_case.get("target_demographic"),
        "special_note": business_case.get("special_note"),
        "society": location.get("society"),
        "local_area": location.get("local_area"),
        "city": location.get("city"),
        "state": location.get("state"),
        "country": location.get("country"),
        "pincode": location.get("pincode"),
        "research_results": {},
        "errors": [],
    }
    
    # Validate required fields
    required_fields = [
        "restaurant_concept", "investment", "target_demographic",
        "city", "state", "country"
    ]
    
    missing_fields = [
        field for field in required_fields 
        if not state.get(field)
    ]
    
    if missing_fields:
        logger.warning(
            f"Missing required fields in config: {', '.join(missing_fields)}"
        )
    
    return state


def print_section_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_evidence_item(item: dict, idx: int) -> None:
    """Print a single evidence item with proper formatting."""
    source = item.get("source", "unknown")
    title = item.get("title", "")
    text = item.get("content", item.get("text", ""))
    
    if title:
        print(f"- {source}: {title}...")
    elif text:
        print(f"- {source}: {text}...")
    else:
        print(f"- {source}: {idx + 1}")


def print_summary(research_results: dict) -> None:
    """Print summary statistics."""
    print_section_header("SUMMARY")
    
    total_evidence = sum(
        len(r.get("evidence", [])) 
        for r in research_results.values()
    )
    successful_sections = sum(
        1 for r in research_results.values() 
        if r.get("status") == "success"
    )
    total_sections = len(research_results)
    
    print(f"Total sections: {total_sections}")
    print(f"Successful: {successful_sections}")
    print(f"Total evidence items: {total_evidence}")
    print("=" * 60)


def main() -> None:
    """Run the research workflow."""
    
    try:
        # Build state from config
        state = build_state_from_config()
        
        # Run workflow
        workflow = ResearchWorkflow()
        result = workflow.run(state)

        # Print results
        print_section_header("RESEARCH WORKFLOW COMPLETED")

        research_results = result.get("research_results", {})
        
        for section_name, section_result in research_results.items():
            print_section_header(f"{section_name}")
            print(f"Status: {section_result.get('status')}")

            evidence = section_result.get("evidence", [])
            print(f"Evidence: {len(evidence)}")

            # Show first 3 evidence items
            for idx, item in enumerate(evidence):
                print_evidence_item(item, idx)

        # Print summary
        print_summary(research_results)

    except Exception as exc:
        logger.exception("Research workflow failed")
        print(f"\n❌ RESEARCH WORKFLOW FAILED")
        print(f"Error: {str(exc)}")
        raise


if __name__ == "__main__":
    main()