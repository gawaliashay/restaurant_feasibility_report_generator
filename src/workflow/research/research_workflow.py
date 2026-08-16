# src\workflow\research\research_workflow.py

"""
Research workflow - Evidence Collection only.

Responsibilities:
- Orchestrate 5 independent research sections
- All sections run in parallel (no dependencies)
- Maintain WorkflowState
- Delegate section execution to ResearchSectionRunner

No tool-specific logic belongs here.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.research.research_section_runner import ResearchSectionRunner


class ResearchWorkflow:
    """Orchestrate evidence collection sections (all independent)."""

    def __init__(self) -> None:
        self.sections = config_loader.get("research.sections", {})
        self.runner = ResearchSectionRunner()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build DAG with all research sections running in parallel."""
        graph = StateGraph(WorkflowState)

        # Only evidence-producing sections (independent)
        # research_sections =
        #     "market_analysis"
        #     "competitive_analysis"
        #     "location_analysis"
        #     "customer_demographics"
        #     "compliance_requirements"

        # Get all enabled sections from config
        enabled_sections = [
            name for name, config in self.sections.items()
            if config.get("enabled", True)
        ]


        # Add nodes for each enabled section
        for section_name in enabled_sections:
            graph.add_node(section_name, self._create_section_node(section_name))

        # All sections start from START and go to END (parallel)
        for section_name in enabled_sections:
            graph.add_edge(START, section_name)
            graph.add_edge(section_name, END)

        return graph.compile()

    # def _build_workflow(self):
    #     """Build DAG with all research sections running in parallel."""
    #     graph = StateGraph(WorkflowState)

    #     # ============================================================
    #     # ADD NODES - 5 Independent Research Sections
    #     # ============================================================

    #     graph.add_node("market_analysis", self._create_section_node("market_analysis"))
    #     graph.add_node("competitive_analysis", self._create_section_node("competitive_analysis"))
    #     graph.add_node("location_analysis", self._create_section_node("location_analysis"))
    #     graph.add_node("customer_demographics", self._create_section_node("customer_demographics"))
    #     graph.add_node("compliance_requirements", self._create_section_node("compliance_requirements"))

    #     # ============================================================
    #     # ADD EDGES - All Start from START, All End at END
    #     # ============================================================

    #     graph.add_edge(START, "market_analysis")
    #     graph.add_edge(START, "competitive_analysis")
    #     graph.add_edge(START, "location_analysis")
    #     graph.add_edge(START, "customer_demographics")
    #     graph.add_edge(START, "compliance_requirements")

    #     graph.add_edge("market_analysis", END)
    #     graph.add_edge("competitive_analysis", END)
    #     graph.add_edge("location_analysis", END)
    #     graph.add_edge("customer_demographics", END)
    #     graph.add_edge("compliance_requirements", END)

    #     return graph.compile()

    def _create_section_node(self, section_name: str):
        """Create a LangGraph node for one research section."""
        def run_section(state: WorkflowState) -> dict[str, Any]:
            logger.info("Running research section: %s", section_name)

            result = self.runner.run(
                section_name=section_name,
                state=state,
            )

            research_results = dict(state.get("research_results", {}))
            research_results[section_name] = result

            return {"research_results": research_results}

        return run_section

    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the research workflow."""
        logger.info("Research workflow started")
        result = self.workflow.invoke(state)
        logger.info("Research workflow completed")
        return result  # type: ignore