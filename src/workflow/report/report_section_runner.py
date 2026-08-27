# src/workflow/report/report_section_runner.py

"""
Generate one report section with the LLM.

Routing: YAML research_section is set → use that evidence.
         YAML research_section is null → use other section reports.
"""

import time
from typing import Any

from src.common.model_loader import model_loader
from src.common.schemas import ReportSectionResult
from src.common.tools.evidence_processor import EvidenceProcessor
from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.graph_states.workflow_states import WorkflowState
from src.logging_exception.logging.logger import logger


class ReportSectionRunner:
    """Generate one configured report section."""

    def __init__(self) -> None:
        self.llm = model_loader.get_llm("analysis_llm")

    def run(self, section_name: str, state: WorkflowState) -> dict[str, Any]:
        """Generate a single report section with retry."""
        retry = config_loader.get("reporting.retry", {})
        max_retries = retry.get("max_retries", 3)
        base_delay = retry.get("backoff_seconds", 1.0)

        sections = config_loader.get("report.sections", {})
        section = sections.get(section_name)

        if not section:
            return ReportSectionResult(
                section=section_name,
                status="failed",
                error="Section not found",
            ).model_dump()

        if not section.get("enabled", True):
            return ReportSectionResult(
                section=section_name,
                status="skipped",
            ).model_dump()

        prompt_name = section.get("prompt")
        if not prompt_name:
            return ReportSectionResult(
                section=section_name,
                status="failed",
                error="No prompt",
            ).model_dump()

        prompt, sources = self._build_prompt(section, state)

        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(prompt)
                report = self._get_text(response)

                if report:
                    logger.info("Report section completed", section=section_name)
                    return ReportSectionResult.model_validate({
                        "section": section_name,
                        "status": "success",
                        "report": report,
                        "sources": sources,
                    }).model_dump()

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.exception("Report section failed", section=section_name)
                    return ReportSectionResult(
                        section=section_name,
                        status="failed",
                        error=str(e),
                    ).model_dump()

                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Report section retry",
                    section=section_name,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_seconds=delay,
                )
                time.sleep(delay)

        return ReportSectionResult(
            section=section_name,
            status="failed",
            error="Max retries exceeded",
        ).model_dump()

    def _build_prompt(
        self,
        section: dict[str, Any],
        state: WorkflowState,
    ) -> tuple[str, list[str]]:
        """Return (prompt text, sources used)."""
        prompt_name = section["prompt"]
        template = prompts_loader.get_prompt("reporting", prompt_name)

        mode = config_loader.get("resource_limits.mode", "fast")
        limits = config_loader.get(f"resource_limits.{mode}", {})

        if section.get("research_section") is None:
            formatted_evidence, sources = self._cross_section_context(state, limits)
        else:
            formatted_evidence, sources = self._evidence_context(
                section["research_section"],
                state,
                limits,
            )

        # Business / location keys all come from state (empty special_note → "None").
        input_keys = (
            "restaurant_concept",
            "investment",
            "target_demographic",
            "society",
            "local_area",
            "city",
            "state",
            "country",
            "pincode",
            "special_note",
        )
        context: dict[str, Any] = {
            key: (state.get(key) or "") for key in input_keys
        }
        context["special_note"] = str(context["special_note"]).strip() or "None"

        common_rules = prompts_loader.get_prompt("reporting", "common_rules", "")
        if "{special_note}" in common_rules:
            common_rules = common_rules.format(special_note=context["special_note"])

        context["section_insights"] = formatted_evidence
        context["common_rules"] = common_rules

        return template.format(**context), sources

    def _evidence_context(
        self,
        research_section: str,
        state: WorkflowState,
        limits: dict[str, Any],
    ) -> tuple[str, list[str]]:
        """Single-section report: use research evidence."""
        research_results = state.get("research_results", {})
        evidence = research_results.get(research_section, {}).get("evidence", [])

        max_items = limits.get("max_tool_results_per_section", 10)
        evidence = self._mix_tools(evidence, max_items)

        sources = EvidenceProcessor.collect_sources(evidence)
        return self._format_evidence(evidence, limits), sources

    @staticmethod
    def _mix_tools(evidence: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
        """Cap items but keep each tool represented.

        Score-sort-then-slice drops Maps (often no score) behind Tavily.
        Round-robin so the LLM sees Maps rows, not only web snippets.
        """
        if not evidence or max_items <= 0:
            return []
        if len(evidence) <= max_items:
            return EvidenceProcessor.sort_by_score(evidence)

        buckets: dict[str, list[dict[str, Any]]] = {}
        for item in evidence:
            tool = str(item.get("tool") or "other")
            buckets.setdefault(tool, []).append(item)
        for tool, items in buckets.items():
            buckets[tool] = EvidenceProcessor.sort_by_score(items)

        selected: list[dict[str, Any]] = []
        while len(selected) < max_items and any(buckets.values()):
            for tool in list(buckets):
                if not buckets[tool]:
                    continue
                selected.append(buckets[tool].pop(0))
                if len(selected) >= max_items:
                    break
        return selected

    def _cross_section_context(
        self,
        state: WorkflowState,
        limits: dict[str, Any],
    ) -> tuple[str, list[str]]:
        """Risk / strategy: summarize other section reports."""
        section_reports = state.get("section_reports", {})
        report_sections = config_loader.get("report.sections", {})
        max_chars = limits.get("max_summary_chars_for_sections", 600)

        insights: list[str] = []
        sources: list[str] = []
        seen: set[str] = set()

        for name, config in report_sections.items():
            if not config.get("enabled", True):
                continue
            if config.get("research_section") is None:
                continue

            result = section_reports.get(name, {})
            if result.get("status") != "success":
                continue

            content = result.get("report", "")
            if not content:
                continue

            title = config.get("title", name)
            insights.append(f"## {title}\n{self._extract_insights(content, max_chars)}")

            for source in result.get("sources", []):
                if source and source not in seen:
                    seen.add(source)
                    sources.append(source)

        text = "\n\n---\n\n".join(insights) if insights else "No section reports available."
        return text, sources

    def _extract_insights(self, content: str, max_chars: int) -> str:
        """Trim to max_chars, preferring a sentence or line break."""
        if len(content) <= max_chars:
            return content

        result = content[:max_chars]

        last_period = result.rfind(". ")
        if last_period != -1 and last_period > max_chars - 50:
            return result[: last_period + 1]

        last_newline = result.rfind("\n")
        if last_newline != -1 and last_newline > max_chars - 50:
            return result[:last_newline]

        last_space = result.rfind(" ")
        if last_space != -1 and last_space > max_chars - 20:
            return result[:last_space] + "..."

        return result

    def _format_evidence(self, evidence: list, limits: dict) -> str:
        """Format evidence blocks for the prompt."""
        if not evidence:
            return "No evidence available."

        max_text_per_result = limits.get("max_text_per_result", 300)
        max_total_chars = limits.get("max_evidence_chars_for_final_report", 6000)

        lines: list[str] = []
        total_chars = 0

        for item in evidence:
            source = item.get("source") or item.get("tool", "Unknown")
            title = item.get("title", "")
            content = item.get("content", "")
            extra = item.get("extra") or {}

            block = [f"Source: {source}"]
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
            if total_chars + len(block_text) > max_total_chars:
                remaining = max_total_chars - total_chars
                if remaining > 50:
                    lines.append(block_text[:remaining])
                break

            lines.append(block_text)
            total_chars += len(block_text)

        return "\n".join(lines)

    def _get_text(self, response: Any) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()