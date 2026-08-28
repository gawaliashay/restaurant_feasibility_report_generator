# src/workflow/research/research_workflow.py

"""LangGraph fan-out: each enabled research section runs in parallel."""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.research.research_section_runner import ResearchSectionRunner


class ResearchWorkflow:
    def __init__(self) -> None:
        self.runner = ResearchSectionRunner()

    def run(self, state: WorkflowState) -> WorkflowState:
        logger.info("Research workflow started")
        sections = config_loader.get("research.sections", {})
        enabled = [name for name, cfg in sections.items() if cfg.get("enabled", True)]

        graph = StateGraph(WorkflowState)
        for name in enabled:
            graph.add_node(name, self._create_section_node(name))
            graph.add_edge(START, name)
            graph.add_edge(name, END)

        result = graph.compile().invoke(state)
        logger.info("Research workflow completed")
        return cast(WorkflowState, result)

    def _create_section_node(self, section_name: str):
        def run_section(state: WorkflowState) -> dict[str, Any]:
            logger.info("Running research section", section=section_name)
            result = self.runner.run(section_name=section_name, state=state)
            return {
                "research_results": {section_name: result},
                "errors": result.get("errors", []),
            }

        return run_section
