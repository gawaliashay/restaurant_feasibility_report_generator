# src\workflow\report\report_section_runner.py

"""
Report Section Runner.

Generates report sections using LLM.
"""

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
        self.sections = config_loader.get("report.sections", {})
        self.llm = model_loader.get_llm("analysis_llm")
        self.compiler = ReportCompiler()

    def run(self, section_name: str, state: WorkflowState) -> dict[str, Any]:
        """Generate a single report section."""
        try:
            section = self.sections.get(section_name)

            if not section:
                return {"section": section_name, "status": "failed", "report": "", "error": "Section not found"}

            if not section.get("enabled", True):
                return {"section": section_name, "status": "skipped", "report": ""}

            # final_compilation: stack reports (no LLM)
            if section_name == "final_compilation":
                logger.info("Compiling final report: %s", section_name)
                return {"section": section_name, "status": "success", "report": self.compiler.compile(dict(state))}

            # All other sections: use LLM
            prompt_name = section.get("prompt")
            if not prompt_name:
                return {"section": section_name, "status": "failed", "report": "", "error": "No prompt"}

            prompt = self._build_prompt(prompt_name, state)
            response = self.llm.invoke(prompt)
            report = self._get_text(response)

            if not report:
                return {"section": section_name, "status": "failed", "report": "", "error": "Empty response"}

            logger.info("Report section completed: %s", section_name)
            return {"section": section_name, "status": "success", "report": report}

        except Exception as e:
            logger.exception("Report section failed: %s", section_name)
            return {"section": section_name, "status": "failed", "report": "", "error": str(e)}

    def _build_prompt(self, prompt_name: str, state: WorkflowState) -> str:
        """Build prompt with context and evidence."""
        template = prompts_loader.get_prompt("reporting", prompt_name)

        # Get evidence: prompt_name → research_section
        research_section = prompt_name.replace("_prompt", "")
        research_results = state.get("research_results", {})
        evidence = research_results.get(research_section, {}).get("evidence", [])

        context = {
            "restaurant_concept": state.get("restaurant_concept", ""),
            "investment": state.get("investment", ""),
            "target_demographic": state.get("target_demographic", ""),
            "local_area": state.get("local_area", ""),
            "city": state.get("city", ""),
            "state": state.get("state", ""),
            "country": state.get("country", ""),
            "section_insights": self._format_evidence(evidence),
            "common_rules": prompts_loader.get_prompt("reporting", "common_rules", ""),
        }

        return template.format(**context)

    def _format_evidence(self, evidence: list) -> str:
        """Format evidence for LLM prompt."""
        if not evidence:
            return "No evidence available."

        lines = []
        for i, item in enumerate(evidence[:30], 1):
            source = item.get("source", "Unknown")
            title = item.get("title", "")
            content = item.get("content", "")
            extra = item.get("extra", {})

            lines.append(f"[{i}] {source}")
            if title:
                lines.append(f"    {title}")
            if content:
                lines.append(f"    {content[:500]}")
            if extra:
                extra_str = ", ".join([f"{k}: {v}" for k, v in extra.items() if v])
                if extra_str:
                    lines.append(f"    {extra_str}")
            lines.append("")

        return "\n".join(lines)

    def _get_text(self, response: Any) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()