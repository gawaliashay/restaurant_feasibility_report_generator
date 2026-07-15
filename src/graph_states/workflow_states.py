# src\graph_states\workflow_states.py

"""
Shared LangGraph state for configuration-driven restaurant research workflow.
State contains runtime data only. Research sections are generated dynamically from YAML.
"""

from typing import Annotated, Any, Dict, List, TypedDict


# =====================================
# STATE REDUCERS
# =====================================

def merge_research_results(
    existing_results: Dict[str, Any],
    new_results: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge parallel section research outputs from multiple nodes."""
    return {**existing_results, **new_results}


def merge_completed_sections(
    existing_sections: List[str],
    new_sections: List[str],
) -> List[str]:
    """Merge completed sections from parallel nodes."""
    return new_sections if new_sections else existing_sections


# =====================================
# LANGGRAPH STATE DEFINITION
# =====================================

class WorkflowState(TypedDict, total=False):
    """
    Shared state passed between LangGraph nodes.
    Uses TypedDict for type safety and reducers for parallel operations.
    """
    
    # ====== Business Context ======
    restaurant_concept: str
    investment: str
    target_demographic: str
    special_note: str
    
    # ====== Location ======
    society: str
    local_area: str
    city: str
    state: str
    pincode: str
    
    # ====== Human Feedback ======
    accept: bool
    extra_instructions: str
    
    # ====== Research Runtime ======
    research_tasks: List[Dict[str, Any]]
    research_results: Annotated[Dict[str, Any], merge_research_results]
    completed_sections: Annotated[List[str], merge_completed_sections]
    
    # ====== Report Generation ======
    final_report: Dict[str, str]
    
    # ====== Export ======
    export_paths: Dict[str, str]
    
    # ====== Metadata ======
    workflow_id: str
    report_timestamp: str