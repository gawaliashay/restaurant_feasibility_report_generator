# src/graph_states/workflow_states.py

"""
Workflow state for the restaurant market research pipeline.
"""

from typing import Any, TypedDict, Annotated, Any
import operator


class WorkflowState(TypedDict, total=False):

    # Business Input
    restaurant_concept: str
    investment: str
    target_demographic: str
    special_note: str

    # Location
    society: str
    local_area: str
    city: str
    state: str
    pincode: str
    country: str

    # Research
    research_results: Annotated[dict[str, Any],operator.or_,]

    # Analysis
    risk_assessment: dict[str, Any]
    strategic_recommendations: dict[str, Any]

    # Report
    final_report: dict[str, Any]
    export_paths: dict[str, Any]

    # Runtime
    errors: list[dict[str, Any]]