"""
Execute one configured research section.

Responsibilities:
- Read section configuration.
- Format configured queries.
- Build tool parameters from configuration.
- Execute tools through the tool pipeline.
- Convert results into evidence.
"""

from typing import Any

from src.common.tools.tool_pipeline import run_tool
from src.configuration.config_loader import config_loader
from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger
from src.workflow.research.evidence_processor import EvidenceProcessor
from src.graph_states.workflow_states import WorkflowState


class ResearchSectionRunner:
    """Execute research sections using configuration."""

    def __init__(self) -> None:
        self.sections = config_loader.get("research.sections", {})
        self.evidence_processor = EvidenceProcessor()

    def run(
        self,
        section_name: str,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Execute one configured research section."""
        try:
            section = self.sections.get(section_name)

            if not section:
                raise CustomException(f"Research section not found: {section_name}")

            if not section.get("enabled", True):
                logger.info("Research section disabled: %s", section_name)
                return {
                    "section": section_name,
                    "status": "skipped",
                    "evidence": [],
                }

            logger.info("Research section started: %s", section_name)
            evidence: list[dict[str, Any]] = []

            for tool_name in section.get("tools", []):
                queries = section.get("queries", {}).get(tool_name, [])
                tool_config = config_loader.get(f"tools.{tool_name}", {})
                query_param = tool_config.get("query_parameter")

                if not query_param:
                    raise CustomException(f"Query parameter not configured: {tool_name}")

                for query_template in queries:
                    # Format query using state
                    query = query_template.format(**state)
                    params = {query_param: query}

                    # Handle location parameter for tools that need it
                    location_param = tool_config.get("location_parameter")
                    if location_param:
                        location_template = tool_config.get("location_template", "{city}, {state}, {country}")
                        try:
                            params[location_param] = location_template.format(**state)
                        except KeyError:
                            params[location_param] = f"{state.get('city', '')}, {state.get('state', '')}"

                    # Execute tool
                    result = run_tool(tool_name, params)

                    if result.get("status") != "success":
                        logger.warning("Tool failed: %s | query=%s", tool_name, query)
                        continue

                    # Convert to evidence
                    evidence.extend(
                        self.evidence_processor.process(
                            tool_name=tool_name,
                            query=query,
                            results=result.get("data"),
                        )
                    )

            logger.info("Research section completed: %s", section_name)

            return {
                "section": section_name,
                "status": "success",
                "evidence": evidence,
            }

        except Exception as exc:
            logger.exception("Research section failed: %s", section_name)
            return {
                "section": section_name,
                "status": "failed",
                "evidence": [],
                "error": str(exc),
            }