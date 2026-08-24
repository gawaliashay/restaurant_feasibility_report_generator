# src/workflow/research/research_section_runner.py

"""
Execute one configured research section.

Read YAML → run tools → normalize evidence → return ResearchSectionResult.
"""

from typing import Any

from src.common.schemas import ResearchSectionResult
from src.common.tools.evidence_processor import EvidenceProcessor
from src.common.tools.tool_pipeline import run_tool
from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger


class ResearchSectionRunner:
    """Execute research sections using configuration."""

    def __init__(self) -> None:
        self.evidence_processor = EvidenceProcessor()

    def run(
        self,
        section_name: str,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Execute one configured research section."""
        try:
            sections = config_loader.get("research.sections", {})
            section = sections.get(section_name)

            if not section:
                raise CustomException(f"Research section not found: {section_name}")

            if not section.get("enabled", True):
                logger.info("Research section disabled", section=section_name)
                return ResearchSectionResult(
                    section=section_name,
                    status="skipped",
                ).model_dump()

            logger.info("Research section started", section=section_name)
            evidence: list[dict[str, Any]] = []
            errors: list[dict[str, Any]] = []

            for tool_name in section.get("tools", []):
                queries = section.get("queries", {}).get(tool_name, [])

                for query_template in queries:
                    query = query_template.format(**state)
                    params: dict[str, Any] = {"query": query}

                    if tool_name == "google_maps":
                        params["location"] = "{city}, {state}, {country}".format(**state)

                    result = run_tool(tool_name, params)

                    if result.get("status") != "success":
                        errors.append({
                            "section": section_name,
                            "tool": tool_name,
                            "query": query,
                            "error": result.get("error", "Tool failed"),
                        })
                        logger.warning(
                            "Tool failed",
                            tool=tool_name,
                            query=query,
                            error=result.get("error"),
                        )
                        continue

                    evidence.extend(
                        self.evidence_processor.process(
                            tool_name=tool_name,
                            query=query,
                            results=result.get("data"),
                        )
                    )

            evidence = self.evidence_processor.dedupe(evidence)
            evidence = self.evidence_processor.sort_by_score(evidence)

            mode = config_loader.get("resource_limits.mode", "fast")
            limits = config_loader.get(f"resource_limits.{mode}", {})
            max_chars = limits.get("max_evidence_chars_per_section", 2000)
            evidence = self.evidence_processor.limit_by_chars(evidence, max_chars)

            sources = self.evidence_processor.collect_sources(evidence)

            logger.info(
                "Research section completed",
                section=section_name,
                evidence_count=len(evidence),
                chars=sum(len(item.get("content", "")) for item in evidence),
                error_count=len(errors),
            )

            return ResearchSectionResult.model_validate({
                            "section": section_name,
                            "status": "success",
                            "evidence": evidence,
                            "sources": sources,
                            "errors": errors,
                        }).model_dump()

        except Exception as exc:
            logger.exception("Research section failed", section=section_name)
            return ResearchSectionResult(
                section=section_name,
                status="failed",
                error=str(exc),
            ).model_dump()