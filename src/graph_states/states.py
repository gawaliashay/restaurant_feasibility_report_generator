# src\graph_states\states.py

from typing import TypedDict, Dict, Any, List, Optional, Annotated
from pydantic import Field, BaseModel


# =====================================
# ANALYST MODELS
# =====================================
class Analyst(BaseModel):
    role: str = Field(description="Role in the context of the restaurant_concept")
    affiliation: str = Field(description="Organisation the analyst belongs to")
    tools: List[str] = Field(description="Tools this analyst can use")
    description: str = Field(description="Responsibilities and focus areas")


# =====================================
# LOCATION MODEL (NEW)
# =====================================
class LocationData(BaseModel):
    society: Optional[str] = None
    local_area: str
    city: str
    state: str
    pincode: str


# =====================================
# CUSTOM REDUCER FOR PARALLEL EXECUTION
# =====================================
def merge_research_results(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Custom reducer to merge research results from parallel executions"""
    if not existing:
        return new
    if not new:
        return existing
    # Merge the dictionaries - both should have single key-value pairs
    return {**existing, **new}

def merge_current_analysts(existing: Optional[str], new: Optional[str]) -> Optional[str]:
    """Reducer for current_analyst - takes the last value"""
    return new if new is not None else existing

def merge_location_data(existing: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Reducer for location data - prefer new data but fall back to existing"""
    return new if new is not None else existing


# =====================================
# RESEARCH STATE TYPEDDICT
# =====================================
class ResearchState(TypedDict, total=False):
    # Business Context Inputs
    restaurant_concept: str
    investment: str
    target_demographic: str
    special_note: str
    
    # Location Context 
    location: Annotated[Optional[Dict[str, Any]], merge_location_data]
    
    # Analyst Generation Control
    max_analysts: int
    retry_count: int
    
    # Analyst Team Management
    dynamic_analysts: List[Analyst]
    analysts_team: List[Analyst]
    
    # Human Feedback System
    accept: bool
    extra_instructions: str
    
    # Research Execution State
    research_tasks: List[Dict]
    research_results: Annotated[Dict[str, Any], merge_research_results]
    research_summary: Dict[str, Any]
    current_task: Dict[str, Any]
    current_analyst: Annotated[Optional[str], merge_current_analysts] 
    
    # Report Compilation State
    executive_summary: str
    market_analysis: str
    financial_recommendations: str
    risk_assessment: str
    implementation_roadmap: str
    conclusion: str
    
    final_report: Dict[str, Any]
    export_paths: Dict[str, str]