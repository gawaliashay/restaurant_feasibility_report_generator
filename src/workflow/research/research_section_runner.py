# src\workflow\research\research_section_runner.py

"""
Execute one configured research section.

Responsibilities:
- Read section configuration.
- Format configured queries.
- Build tool parameters from configuration.
- Execute tools through the tool pipeline.
- Convert results into evidence.
- Apply section-level evidence limits.
"""

from typing import Any

from src.common.tools.tool_pipeline import run_tool
from src.configuration.config_loader import config_loader
from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger
from src.common.tools.evidence_processor import EvidenceProcessor
from src.graph_states.workflow_states import WorkflowState


class ResearchSectionRunner:
    """Execute research sections using configuration."""

    def __init__(self) -> None:
        # Only non-config dependencies
        self.evidence_processor = EvidenceProcessor()

    def run(
        self,
        section_name: str,
        state: WorkflowState,
    ) -> dict[str, Any]:
        """Execute one configured research section."""
        try:
            # Lazy load config at point of use
            sections = config_loader.get("research.sections", {})
            section = sections.get(section_name)

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

            # ============================================================
            # Step 1: Execute all tools for this section
            # ============================================================
            for tool_name in section.get("tools", []):
                queries = section.get("queries", {}).get(tool_name, [])
                tool_config = config_loader.get(f"tools.{tool_name}", {})
                query_param = tool_config.get("query_parameter")

                if not query_param:
                    raise CustomException(f"Query parameter not configured: {tool_name}")

                for query_template in queries:
                    # Format query using state variables
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

                    # Convert raw tool output to standardized evidence
                    evidence.extend(
                        self.evidence_processor.process(
                            tool_name=tool_name,
                            query=query,
                            results=result.get("data"),
                        )
                    )

            # ============================================================
            # Step 2: Remove duplicate evidence
            # ============================================================
            evidence = self._remove_duplicates(evidence)

            # ============================================================
            # Step 3: Sort by relevance score (highest first)
            # ============================================================
            evidence = self._sort_by_score(evidence)

            # ============================================================
            # Step 4: Apply character limit per section
            # ============================================================
            mode = config_loader.get("resource_limits.mode", "fast")
            limits = config_loader.get(f"resource_limits.{mode}", {})
            max_chars = limits.get("max_evidence_chars_per_section", 2000)
            evidence = self._limit_evidence_by_chars(evidence, max_chars)

            logger.info(
                "Research section completed: %s (%d evidence items, %d chars)",
                section_name,
                len(evidence),
                sum(len(e.get("content", "")) for e in evidence)
            )

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

    def _remove_duplicates(self, evidence: list) -> list:
        """
        Remove duplicate evidence items.
        Uses source + title as unique key.
        """
        seen = set()
        unique = []

        for item in evidence:
            source = item.get("source", "")
            title = item.get("title", "")
            key = source + ":" + title

            # Skip if we've seen this before
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    def _sort_by_score(self, evidence: list) -> list:
        """
        Sort evidence by relevance score (highest first).
        Items with score go first, items without score go last.
        """
        with_score = []
        without_score = []

        # Separate items with and without scores
        for item in evidence:
            score = item.get("extra", {}).get("score")
            if score is not None:
                with_score.append(item)
            else:
                without_score.append(item)

        # Simple bubble sort - put highest score first
        for i in range(len(with_score)):
            for j in range(i + 1, len(with_score)):
                score_i = with_score[i].get("extra", {}).get("score", 0)
                score_j = with_score[j].get("extra", {}).get("score", 0)
                if score_i < score_j:
                    # Swap
                    with_score[i], with_score[j] = with_score[j], with_score[i]

        # Items with score first, then items without score
        return with_score + without_score

    def _limit_evidence_by_chars(
        self,
        evidence: list[dict[str, Any]],
        max_chars: int
    ) -> list[dict[str, Any]]:
        """
        Limit evidence by total character count.
        Keeps adding evidence until max_chars is reached.
        """
        if not evidence:
            return []

        limited = []
        total_chars = 0

        for item in evidence:
            content = item.get("content", "")
            remaining = max_chars - total_chars

            # Stop if we've reached the limit
            if remaining <= 0:
                break

            # Copy item and truncate content if needed
            item_copy = item.copy()
            item_copy["content"] = content[:remaining]
            limited.append(item_copy)

            # Track total characters used
            total_chars += len(item_copy["content"])

        return limited