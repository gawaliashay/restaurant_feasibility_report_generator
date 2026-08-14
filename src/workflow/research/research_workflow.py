"""
Research workflow.

Responsibilities:
- Orchestrate configured research sections.
- Resolve section dependencies.
- Maintain WorkflowState.
- Delegate section execution to ResearchSectionRunner.

No tool-specific logic belongs here.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.research.research_section_runner import ResearchSectionRunner


class ResearchWorkflow:
    """Orchestrate configured research sections."""

    def __init__(self) -> None:
        self.sections = config_loader.get("research.sections", {})
        self.runner = ResearchSectionRunner()
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        """Build the research DAG from configuration."""
        graph = StateGraph(WorkflowState)

        # Get enabled sections
        enabled_sections = [
            name for name, config in self.sections.items()
            if config.get("enabled", True)
        ]

        # Add nodes for each enabled section
        for section_name in enabled_sections:
            graph.add_node(section_name, self._create_section_node(section_name))

        # Add edges based on dependencies
        for section_name in enabled_sections:
            dependencies = self.sections[section_name].get("dependencies", [])
            # Filter out disabled dependencies
            dependencies = [d for d in dependencies if d in enabled_sections]

            if not dependencies:
                graph.add_edge(START, section_name)
            else:
                for dependency in dependencies:
                    graph.add_edge(dependency, section_name)

        # Add edges to END for sections with no dependents
        for section_name in enabled_sections:
            has_dependents = any(
                section_name in self.sections[other].get("dependencies", [])
                for other in enabled_sections
            )
            if not has_dependents:
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