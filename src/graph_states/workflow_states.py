# src/graph_states/workflow_states.py

"""
Workflow state for the restaurant market research pipeline.
"""

import operator
from typing import Annotated, Any, TypedDict


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

    # Research Evidence
    research_results: Annotated[dict[str, Any], operator.or_]

    # Section Reports
    section_reports: Annotated[dict[str, Any], operator.or_]

    # Cross-section Analysis
    risk_assessment: dict[str, Any]
    strategic_recommendations: dict[str, Any]

    # Final Report
    final_report: dict[str, Any]
    export_paths: dict[str, Any]

    # Runtime
    errors: Annotated[list[dict[str, Any]], operator.add]