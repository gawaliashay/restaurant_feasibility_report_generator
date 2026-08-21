# src\workflow\research\research_workflow.py

"""
Research workflow - Evidence Collection only.

Responsibilities:
- Orchestrate independent research sections
- Run enabled sections in parallel
- Maintain workflow state
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
    """Orchestrate independent evidence collection sections."""

    def __init__(self) -> None:
        self.runner = ResearchSectionRunner()

    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the research workflow."""
        logger.info("Research workflow started")

        # Lazy load sections and build workflow at point of use
        sections = config_loader.get("research.sections", {})
        workflow = self._build_workflow(sections)
        result = workflow.invoke(state)

        logger.info("Research workflow completed")
        return result  # type: ignore

    def _build_workflow(self, sections: dict) -> Any:
        """
        Build a DAG where every enabled research section runs independently.

        Sections are loaded dynamically from configuration and follow:

            START → Research Section → END

        This allows new independent research sections to be added
        through configuration without modifying the workflow code.
        """

        graph = StateGraph(WorkflowState)

        enabled_sections = [
            name
            for name, config in sections.items()
            if config.get("enabled", True)
        ]

        for section_name in enabled_sections:
            graph.add_node(
                section_name,
                self._create_section_node(section_name),
            )

            graph.add_edge(START, section_name)
            graph.add_edge(section_name, END)

        return graph.compile()

    def _create_section_node(self, section_name: str):
        """Create a LangGraph node for one research section."""

        def run_section(state: WorkflowState) -> dict[str, Any]:
            logger.info("Running research section: %s", section_name)

            result = self.runner.run(
                section_name=section_name,
                state=state,
            )

            return {
                "research_results": {
                    section_name: result
                }
            }

        return run_section