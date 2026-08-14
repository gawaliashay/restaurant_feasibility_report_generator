"""
Application entry point.

Responsibilities:
- Load the configured business case.
- Start the configured research workflow.
- Pass workflow state between pipeline stages.
- Return the final pipeline result.

Business logic belongs to the workflow modules.
Configuration belongs to configs.yaml.
Tool execution belongs to the common tool pipeline.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from src.configuration.config_loader import config_loader
from src.workflow.research_orchestrator import research_orchestrator


logger = logging.getLogger(__name__)


def build_initial_state() -> Dict[str, Any]:
    """Build the initial pipeline state from configuration."""
    
    business_case = config_loader.get(
        "business_case.default",
        {},
    )

    if not isinstance(
        business_case,
        dict,
    ):
        raise ValueError(
            "business_case.default must be a dictionary"
        )

    # Start with empty state
    state: Dict[str, Any] = {}

    # Copy top-level fields
    for key, value in business_case.items():
        if key == "location":
            # Flatten location into top-level fields
            if isinstance(value, dict):
                for loc_key, loc_value in value.items():
                    if not isinstance(loc_value, (dict, list, tuple, set)):
                        state[loc_key] = loc_value
                        print(f"  📍 Flattened location: {loc_key} = {loc_value}")
        elif not isinstance(value, (dict, list, tuple, set)):
            state[key] = value
            print(f"  📍 Added top-level: {key} = {value}")

    # Add workflow metadata
    state["workflow_id"] = str(uuid.uuid4())
    state["started_at"] = datetime.now().isoformat()

    print(f"\n📋 Final state keys: {list(state.keys())}")
    print(f"📋 city: {state.get('city')}")
    print(f"📋 local_area: {state.get('local_area')}")
    print()

    return state


def run_pipeline() -> Dict[str, Any]:
    """
    Execute the configured research pipeline.
    """

    logger.info("Pipeline execution started")

    state = build_initial_state()

    # The orchestrator accepts Dict[str, Any] but the type hint says WorkflowState
    # This is safe because WorkflowState is a TypedDict of Dict[str, Any]
    result = research_orchestrator.run(state)  # type: ignore

    logger.info(
        "Pipeline execution completed | status=%s",
        result.get("status"),
    )

    return result


def main() -> None:
    """Run the pipeline from the command line."""

    result = run_pipeline()

    status = result.get(
        "status",
        "failed",
    )

    print(f"\nPipeline status: {status}")

    research_results = result.get("research_results", {})
    if research_results:
        completed = [
            name for name, res in research_results.items()
            if isinstance(res, dict) and res.get("status") == "success"
        ]
        failed = [
            name for name, res in research_results.items()
            if isinstance(res, dict) and res.get("status") == "failed"
        ]
        print(f"Sections: {len(completed)} completed, {len(failed)} failed")


if __name__ == "__main__":
    main()