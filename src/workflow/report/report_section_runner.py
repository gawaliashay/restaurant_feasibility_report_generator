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
        template = prompts_loader.get_prompt("reporting", prompt_name)
        research_results = state.get("research_results", {})
        
        # Map prompt → research section
        prompt_to_research = {
            "market_analysis_prompt": "market_analysis",
            "competitive_analysis_prompt": "competitive_analysis",
            "location_analysis_prompt": "location_analysis",
            "customer_demographics_prompt": "customer_demographics",
            "compliance_requirements_prompt": "compliance_requirements",
            "risk_assessment_prompt": None,
            "strategic_recommendations_prompt": None,
        }
        
        # Cross-section prompts get ALL evidence (distributed evenly across sections)
        if prompt_name in ["risk_assessment_prompt", "strategic_recommendations_prompt"]:
            sections_list = ["market_analysis", "competitive_analysis", "location_analysis", 
                        "customer_demographics", "compliance_requirements"]
            section_evidence = {}
            for section in sections_list:
                section_evidence[section] = research_results.get(section, {}).get("evidence", [])

            quality_mode = config_loader.get("report_quality.mode", "balanced")
            max_items = config_loader.get(f"report_quality.{quality_mode}.max_tool_results_cross_section", 35)
            per_section = max(1, max_items // len(sections_list))
            all_evidence = []
            for section in sections_list:
                all_evidence.extend(section_evidence[section][:per_section])
            formatted_evidence = self._format_evidence(all_evidence, cross_section=True)

        else:
            # ✅ FIX: Get the research section name, default to empty string
            research_section = prompt_to_research.get(prompt_name, "")
            evidence = research_results.get(research_section, {}).get("evidence", []) if research_section else []
            formatted_evidence = self._format_evidence(evidence)
        
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

    def _format_evidence(self, evidence: list, cross_section: bool = False) -> str:
        if not evidence:
            return "No evidence available."

        quality_mode = config_loader.get("report_quality.mode", "balanced")
        key = f"report_quality.{quality_mode}"

        if cross_section:
            max_items = config_loader.get(f"{key}.max_tool_results_cross_section", 35)
        else:
            max_items = config_loader.get(f"{key}.max_tool_results_per_section", 12)

        max_chars = config_loader.get("research.limits.max_text_per_result", 300)

        lines = []
        for item in evidence[:max_items]:
            source = item.get("source") or item.get("tool", "Unknown")
            title = item.get("title", "")
            content = item.get("content", "")
            extra = item.get("extra") or {}

            lines.append(f"Source: {source}")
            if title:
                lines.append(f"    Title: {title}")
            if content:
                lines.append(f"    {content[:max_chars]}")
            if extra:
                extra_text = " | ".join(
                    f"{k}: {v}" for k, v in extra.items() if v not in (None, "")
                )
                if extra_text:
                    lines.append(f"    {extra_text}")
            lines.append("")

        return "\n".join(lines)

    def _get_text(self, response: Any) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()