# src/workflow/report/report_workflow.py

"""LangGraph DAG: report sections → risk → strategy (from configs.yaml dependencies)."""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.report.report_section_runner import ReportSectionRunner


class ReportWorkflow:
    def __init__(self) -> None:
        self.runner = ReportSectionRunner()

    def run(self, state: WorkflowState) -> WorkflowState:
        logger.info("Starting report workflow")
        sections = config_loader.get("report.sections", {})
        enabled = [name for name, cfg in sections.items() if cfg.get("enabled", True)]

        graph = StateGraph(WorkflowState)
        for name in enabled:
            graph.add_node(name, self._create_node(name))

        for name in enabled:
            if not sections[name].get("dependencies", []):
                graph.add_edge(START, name)

        for name in enabled:
            for dep in sections[name].get("dependencies", []):
                graph.add_edge(dep, name)

        has_dependents = {
            dep for name in enabled for dep in sections[name].get("dependencies", [])
        }
        for name in enabled:
            if name not in has_dependents:
                graph.add_edge(name, END)

        result = graph.compile().invoke(state)
        logger.info("Report workflow completed")
        return cast(WorkflowState, result)

    def _create_node(self, section_name: str):
        def node(state: WorkflowState) -> dict[str, Any]:
            result = self.runner.run(section_name, state)
            logger.info("Report node finished", section=section_name, status=result.get("status"))
            return {"section_reports": {section_name: result}}

        return node
