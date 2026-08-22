# src\workflow\report\report_section_runner.py

"""
Report Section Runner.

Generates report sections using LLM with exponential backoff retry.
"""

import time
from typing import Any

from src.common.model_loader import model_loader
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger
from src.workflow.report.report_compiler import ReportCompiler


class ReportSectionRunner:
    """Generate one configured report section."""

    def __init__(self) -> None:
        # Only non-config dependencies
        self.llm = model_loader.get_llm("analysis_llm")
        self.compiler = ReportCompiler()

    def run(self, section_name: str, state: WorkflowState) -> dict[str, Any]:
        """Generate a single report section with retry."""
        # Lazy load config at point of use
        retry = config_loader.get("reporting.retry", {})
        max_retries = retry.get("max_retries", 3)
        base_delay = retry.get("backoff_seconds", 1.0)

        sections = config_loader.get("report.sections", {})
        section = sections.get(section_name)

        if not section:
            return {"section": section_name, "status": "failed", "report": "", "error": "Section not found"}

        if not section.get("enabled", True):
            return {"section": section_name, "status": "skipped", "report": ""}

        # Special case: final compilation uses ReportCompiler, not LLM
        if section_name == "final_compilation":
            logger.info("Compiling final report: %s", section_name)
            return {
                "section": section_name,
                "status": "success",
                "report": self.compiler.compile(dict(state))
            }

        prompt_name = section.get("prompt")
        if not prompt_name:
            return {"section": section_name, "status": "failed", "report": "", "error": "No prompt"}

        prompt = self._build_prompt(prompt_name, state)

        # Retry with exponential backoff
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(prompt)
                report = self._get_text(response)

                if report:
                    logger.info("Report section completed: %s", section_name)
                    return {"section": section_name, "status": "success", "report": report}

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.exception("Report section failed: %s", section_name)
                    return {"section": section_name, "status": "failed", "report": "", "error": str(e)}

                delay = base_delay * (2 ** attempt)
                logger.warning("Retry %d/%d for %s in %.1fs", attempt + 1, max_retries, section_name, delay)
                time.sleep(delay)

        return {"section": section_name, "status": "failed", "report": "", "error": "Max retries exceeded"}

    def _build_prompt(self, prompt_name: str, state: WorkflowState) -> str:
        """Build the prompt with evidence and context."""
        template = prompts_loader.get_prompt("reporting", prompt_name)
        research_results = state.get("research_results", {})

        # Load resource limits
        mode = config_loader.get("resource_limits.mode", "fast")
        limits = config_loader.get(f"resource_limits.{mode}", {})
        report_sections = config_loader.get("report.sections", {})

        # ============================================================
        # Cross-section reports (Risk Assessment, Strategic Recommendations)
        # Use summarized versions of existing reports
        # ============================================================
        if prompt_name in ["risk_assessment_prompt", "strategic_recommendations_prompt"]:
            section_reports = state.get("section_reports", {})
            insights = []

            # Each report is truncated to this many characters
            max_chars_per_section = limits.get("max_summary_chars_for_sections", 600)

            # Collect all section reports
            for section_name, section_config in report_sections.items():
                # Skip disabled sections
                if not section_config.get("enabled", True):
                    continue
                # Skip cross-section sections (they are added separately)
                if section_config.get("research_section") is None:
                    continue

                report_result = section_reports.get(section_name, {})
                if report_result.get("status") == "success":
                    title = section_config.get("title", section_name)
                    content = report_result.get("report", "")
                    if content:
                        # Extract key insights instead of hard truncation
                        summary = self._extract_insights(content, max_chars_per_section)
                        insights.append(f"## {title}\n{summary}")

            formatted_evidence = "\n\n---\n\n".join(insights) if insights else "No section reports available."

        # ============================================================
        # Single section reports (Market, Competitive, Location, etc.)
        # Use research evidence directly
        # ============================================================
        else:
            research_section = prompt_name.replace("_prompt", "")
            evidence = research_results.get(research_section, {}).get("evidence", [])

            # Sort by score before taking top items
            evidence = self._sort_by_score(evidence)

            # Limit number of evidence items
            max_items = limits.get("max_tool_results_per_section", 10)
            evidence = evidence[:max_items]

            formatted_evidence = self._format_evidence(evidence, limits)

        # Build the final context for the prompt
        context = {
            "restaurant_concept": state.get("restaurant_concept", ""),
            "investment": state.get("investment", ""),
            "target_demographic": state.get("target_demographic", ""),
            "local_area": state.get("local_area", ""),
            "city": state.get("city", ""),
            "state": state.get("state", ""),
            "country": state.get("country", ""),
            "section_insights": formatted_evidence,
            "common_rules": prompts_loader.get_prompt("reporting", "common_rules", ""),
        }

        return template.format(**context)

    def _extract_insights(self, content: str, max_chars: int) -> str:
        """
        Extract first meaningful part of content.
        Tries to end at a period or newline to avoid cutting mid-sentence.
        """
        # If content is short enough, return it all
        if len(content) <= max_chars:
            return content

        # Take first max_chars characters
        result = content[:max_chars]

        # Try to end at a period within the last 50 characters
        last_period = result.rfind(". ")
        if last_period != -1 and last_period > max_chars - 50:
            return result[:last_period + 1]

        # Try to end at a newline within the last 50 characters
        last_newline = result.rfind("\n")
        if last_newline != -1 and last_newline > max_chars - 50:
            return result[:last_newline]

        # If we're in the middle of a word, cut at last space
        last_space = result.rfind(" ")
        if last_space != -1 and last_space > max_chars - 20:
            return result[:last_space] + "..."

        return result

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

    def _format_evidence(self, evidence: list, limits: dict) -> str:
        """Format evidence for the prompt."""
        if not evidence:
            return "No evidence available."

        max_text_per_result = limits.get("max_text_per_result", 300)
        max_total_chars = limits.get("max_evidence_chars_for_final_report", 6000)

        lines = []
        total_chars = 0

        for item in evidence:
            source = item.get("source") or item.get("tool", "Unknown")
            title = item.get("title", "")
            content = item.get("content", "")
            extra = item.get("extra") or {}

            # Build a block for this evidence item
            block = []
            block.append(f"Source: {source}")
            if title:
                block.append(f"    Title: {title}")
            if content:
                block.append(f"    {content[:max_text_per_result]}")
            if extra:
                extra_text = " | ".join(f"{k}: {v}" for k, v in extra.items() if v)
                if extra_text:
                    block.append(f"    {extra_text}")
            block.append("")

            block_text = "\n".join(block)

            # Stop if we exceed the total character limit
            if total_chars + len(block_text) > max_total_chars:
                remaining = max_total_chars - total_chars
                if remaining > 50:
                    lines.append(block_text[:remaining])
                break

            lines.append(block_text)
            total_chars += len(block_text)

        return "\n".join(lines)

    def _get_text(self, response: Any) -> str:
        """Extract text from LLM response."""
        content = getattr(response, "content", response)
        return str(content).strip()