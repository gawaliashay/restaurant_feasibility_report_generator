# src/workflow/research/research_section_runner.py

"""Run tools for one research section; return normalized evidence."""

from typing import Any

from src.common.schemas import ResearchSectionResult
from src.common.tools.evidence_processor import EvidenceProcessor
from src.common.tools.tool_pipeline import run_tool
from src.configuration.config_loader import config_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger


class ResearchSectionRunner:
    def __init__(self) -> None:
        self.evidence_processor = EvidenceProcessor()

    def run(self, section_name: str, state: WorkflowState) -> dict[str, Any]:
        try:
            section = config_loader.get("research.sections", {}).get(section_name)
            if not section:
                raise CustomException(f"Research section not found: {section_name}")

            if not section.get("enabled", True):
                logger.info("Research section disabled", section=section_name)
                return ResearchSectionResult(section=section_name, status="skipped").model_dump()

            logger.info("Research section started", section=section_name)
            evidence: list[dict[str, Any]] = []
            errors: list[dict[str, Any]] = []

            for tool_name in section.get("tools", []):
                for query_template in section.get("queries", {}).get(tool_name, []):
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
                        logger.warning("Tool failed", tool=tool_name, query=query, error=result.get("error"))
                        continue

                    evidence.extend(
                        self.evidence_processor.process(
                            tool_name=tool_name, query=query, results=result.get("data"),
                        )
                    )

            evidence = self.evidence_processor.dedupe(evidence)
            evidence = self.evidence_processor.sort_by_score(evidence)
            mode = config_loader.get("resource_limits.mode", "fast")
            max_chars = config_loader.get(f"resource_limits.{mode}", {}).get(
                "max_evidence_chars_per_section", 2000,
            )
            evidence = self.evidence_processor.limit_by_chars(evidence, max_chars)

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
                "sources": self.evidence_processor.collect_sources(evidence),
                "errors": errors,
            }).model_dump()

        except Exception as exc:
            logger.exception("Research section failed", section=section_name)
            return ResearchSectionResult(
                section=section_name, status="failed", error=str(exc),
            ).model_dump()
