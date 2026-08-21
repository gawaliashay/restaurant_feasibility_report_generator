# src\workflow\report\report_workflow.py

"""
Report Workflow.

Orchestrates report generation using LangGraph.
"""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.report.report_section_runner import ReportSectionRunner


class ReportWorkflow:
    """Build and run the report generation workflow."""

    def __init__(self) -> None:
        self.runner = ReportSectionRunner()

    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the report workflow."""
        logger.info("Starting report workflow")

        # Lazy load sections at point of use
        sections = config_loader.get("report.sections", {})

        enabled = [
            name for name, config in sections.items()
            if config.get("enabled", True)
        ]

        graph = StateGraph(WorkflowState)

        # Add nodes
        for section_name in enabled:
            graph.add_node(section_name, self._create_node(section_name))

        # Add START edges (no dependencies)
        for section_name in enabled:
            if not sections[section_name].get("dependencies", []):
                graph.add_edge(START, section_name)

        # Add dependency edges
        for section_name in enabled:
            for dependency in sections[section_name].get("dependencies", []):
                graph.add_edge(dependency, section_name)

        # Add END edges (no dependents)
        has_dependents = set()
        for section_name in enabled:
            for dependency in sections[section_name].get("dependencies", []):
                has_dependents.add(dependency)

        for section_name in enabled:
            if section_name not in has_dependents:
                graph.add_edge(section_name, END)

        result = graph.compile().invoke(state)

        logger.info("Report workflow completed")
        return cast(WorkflowState, result)

    def _create_node(self, section_name: str):
        def node(state: WorkflowState) -> dict[str, Any]:
            result = self.runner.run(section_name, state)
            logger.info("Report node: %s | %s", section_name, result.get("status"))
            return {"section_reports": {section_name: result}}
        return node