"""
Application entry point for research workflow.
"""

import json
from datetime import datetime
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
        logger.warning(f"Missing required fields: {', '.join(missing_fields)}")

    return state


def print_section_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_full_evidence(item: dict, idx: int) -> None:
    """Print complete evidence item with all details."""
    print(f"\n--- Evidence #{idx + 1} ---")
    print(f"Tool: {item.get('tool', 'unknown')}")
    print(f"Query: {item.get('query', '')}")
    print(f"Source: {item.get('source', 'unknown')}")
    print(f"Title: {item.get('title', 'No title')}")
    print(f"URL: {item.get('url', 'No URL')}")
    print(f"Content:\n{item.get('content', 'No content')}")
    print("-" * 40)


def print_evidence_item(item: dict, idx: int) -> None:
    """Print a single evidence item with proper formatting."""
    source = item.get("source", "unknown")
    title = item.get("title", "")
    text = item.get("content", item.get("text", ""))

    if title:
        print(f"  {idx+1}. {source}: {title}")
    elif text:
        print(f"  {idx+1}. {source}: {text[:80]}...")
    else:
        print(f"  {idx+1}. {source}: No content")


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


def print_full_section_result(section_name: str, section_result: dict) -> None:
    """Print complete section result with all evidence."""
    print_section_header(section_name.replace("_", " ").title())
    print(f"Status: {section_result.get('status')}")

    evidence = section_result.get("evidence", [])
    print(f"Total Evidence: {len(evidence)}")

    if section_result.get("error"):
        print(f"Error: {section_result.get('error')}")

    if evidence:
        print("\n" + "-" * 40)
        print("FULL EVIDENCE DETAILS")
        print("-" * 40)

        # Print all evidence with full details
        for idx, item in enumerate(evidence):
            print_full_evidence(item, idx)

        # Also print summary list
        print("\n" + "-" * 40)
        print("EVIDENCE SUMMARY")
        print("-" * 40)
        for idx, item in enumerate(evidence):
            print_evidence_item(item, idx)

    print("\n" + "=" * 60)


def print_section_summary(section_name: str, section_result: dict) -> None:
    """Print a summary of section results."""
    print_section_header(section_name.replace("_", " ").title())
    print(f"Status: {section_result.get('status')}")

    evidence = section_result.get("evidence", [])
    print(f"Evidence: {len(evidence)}")

    # Show first 5 evidence items as preview
    for idx, item in enumerate(evidence[:5]):
        print_evidence_item(item, idx)

    if len(evidence) > 5:
        print(f"  ... and {len(evidence) - 5} more")

    if section_result.get("error"):
        print(f"Error: {section_result.get('error')}")


def save_results_to_json(research_results: dict, output_dir: str = "reports") -> str:
    """
    Save research results to JSON file.
    
    Args:
        research_results: Dictionary of research results
        output_dir: Directory to save the file
        
    Returns:
        Path to the saved file
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/research_results_{timestamp}.json"
    
    # Prepare data for JSON serialization
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "total_sections": len(research_results),
        "results": research_results
    }
    
    # Save to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)
    
    return filename


def save_evidence_to_json(research_results: dict, output_dir: str = "reports") -> str:
    """
    Save only evidence items to JSON file (flattened).
    
    Args:
        research_results: Dictionary of research results
        output_dir: Directory to save the file
        
    Returns:
        Path to the saved file
    """
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/evidence_{timestamp}.json"
    
    # Collect all evidence with section info
    all_evidence = []
    for section_name, section_result in research_results.items():
        for item in section_result.get("evidence", []):
            all_evidence.append({
                "section": section_name,
                **item
            })
    
    # Prepare data for JSON serialization
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "total_evidence": len(all_evidence),
        "evidence": all_evidence
    }
    
    # Save to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)
    
    return filename


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

        # Default to full details
        output_mode = "full"  # Change to "summary" for brief output

        for section_name, section_result in research_results.items():
            if output_mode == "full":
                print_full_section_result(section_name, section_result)
            else:
                print_section_summary(section_name, section_result)

        # Print summary
        print_summary(research_results)

        # ============================================================
        # SAVE TO JSON FILES
        # ============================================================
        print_section_header("SAVING RESULTS")

        # Save full research results
        results_file = save_results_to_json(research_results)
        print(f"✅ Full results saved to: {results_file}")

        # Save flattened evidence
        evidence_file = save_evidence_to_json(research_results)
        print(f"✅ Evidence only saved to: {evidence_file}")

        print("=" * 60)

    except Exception as exc:
        logger.exception("Research workflow failed")
        print(f"\n❌ RESEARCH WORKFLOW FAILED")
        print(f"Error: {str(exc)}")
        raise


if __name__ == "__main__":
    main()