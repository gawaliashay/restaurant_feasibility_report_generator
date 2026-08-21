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
        
        mode = config_loader.get("resource_limits.mode", "fast")
        limits = config_loader.get(f"resource_limits.{mode}", {})
        
        # Find which report section has this prompt
        report_sections = config_loader.get("report.sections", {})
        research_section = None
        
        for section_name, section_config in report_sections.items():
            if section_config.get("prompt") == prompt_name:
                research_section = section_config.get("research_section")
                break
        
        if research_section:
            # Single section
            evidence = research_results.get(research_section, {}).get("evidence", [])
            max_items = limits.get("max_tool_results_per_section", 10)
            evidence = evidence[:max_items]
            formatted_evidence = self._format_evidence(evidence, limits)
        else:
            # Cross-section (null = use all)
            sections = config_loader.get("research.sections", {})
            all_evidence = []
            for section_name in sections.keys():
                evidence = research_results.get(section_name, {}).get("evidence", [])
                all_evidence.extend(evidence)
            
            max_items = limits.get("max_tool_results_cross_section", 25)
            all_evidence = all_evidence[:max_items]
            formatted_evidence = self._format_evidence(all_evidence, limits)
        
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