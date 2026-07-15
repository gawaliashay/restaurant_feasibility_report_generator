# src\workflow\report_compiler.py

"""
Report Compiler - Generates report from evidence using LangGraph.
Simple workflow: generate_report → export_report
"""

import os
from datetime import datetime
from typing import Any, Dict, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langsmith.run_helpers import traceable

from src.configuration.config_loader import config_loader
from src.configuration.prompts_loader import prompts_loader
from src.common.model_loader import model_loader
from src.logging_exception.logging.logger import logger
from src.utils.report_exporter import save_json_generic, save_markdown_generic
from src.graph_states.workflow_states import WorkflowState


class ReportCompiler:
    """Generates and exports report from research evidence."""

    def __init__(self):
        config = config_loader.get_all()
        
        self.sections = config.get("research", {}).get("sections", {})
        self.export_config = config.get("export", {})
        self.reporting_config = config.get("reporting", {})
        
        quality = config.get('report_quality', {}).get('balanced', {})
        self.max_evidence_chars = quality.get('max_evidence_chars_per_section', 1000)
        
        self.llm = model_loader.get_llm("creative_llm")
        self.prompts = self._load_prompts()
        self.common_rules = prompts_loader.get_prompt("reporting", "common_rules")
        self.workflow = self._build_workflow()

    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts for enabled sections."""
        prompts = {}
        for name, config in self.sections.items():
            if config.get("enabled"):
                prompt_name = config.get("prompt")
                if prompt_name:
                    prompts[name] = prompts_loader.get_chat_prompt("reporting", prompt_name)
        return prompts

    def _build_context(self, state: WorkflowState) -> Dict[str, str]:
        """Build context dictionary from state."""
        return {
            "restaurant_concept": state.get("restaurant_concept", ""),
            "investment": state.get("investment", ""),
            "target_demographic": state.get("target_demographic", ""),
            "special_note": state.get("special_note", ""),
            "society": state.get("society", ""),
            "local_area": state.get("local_area", ""),
            "city": state.get("city", ""),
            "state": state.get("state", ""),
            "pincode": state.get("pincode", ""),
        }

    def _get_evidence(self, state: WorkflowState, section_name: str) -> str:
        """Get evidence for a section, truncate if needed."""
        results = state.get("research_results", {})
        section_data = results.get(section_name, {})
        evidence = str(section_data.get("evidence", section_data.get("research_data", "")))
        
        if len(evidence) > self.max_evidence_chars:
            half = self.max_evidence_chars // 2
            evidence = evidence[:half] + "\n\n... [Truncated] ...\n\n" + evidence[-half:]
        
        return evidence

    # ===============================================================
    # LANGGRAPH NODE 1: Generate Report
    # ===============================================================

    def generate_report(self, state: WorkflowState) -> WorkflowState:
        """Generate report from research evidence."""
        logger.info("Generating report for %s sections", len(self.prompts))
        
        context = self._build_context(state)
        report = {}
        
        for section_name, prompt_template in self.prompts.items():
            evidence = self._get_evidence(state, section_name)
            
            # Build prompt
            prompt = prompt_template.format(
                **context,
                section_evidence=evidence,
                common_rules=self.common_rules,
            )
            
            response = self.llm.invoke(prompt)
            report[section_name] = response.content.strip() if response.content else ""
        
        logger.info("Generated %s sections", len(report))
        return {"final_report": report}

    # ===============================================================
    # LANGGRAPH NODE 2: Export Report
    # ===============================================================

    def export_report(self, state: WorkflowState) -> WorkflowState:
        """Export report to files."""
        report = state.get("final_report", {})
        if not report:
            logger.warning("No report to export")
            return {"export_paths": {}}
        
        directory = self.reporting_config.get("reports_directory", "reports")
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime(
            self.export_config.get("timestamp_format", "%Y%m%d_%H%M%S")
        )
        
        paths = {}
        for fmt in self.export_config.get("formats", ["json", "md"]):
            filepath = os.path.join(directory, f"restaurant_report_{timestamp}.{fmt}")
            
            if fmt == "json":
                saved = save_json_generic(report, filepath)
            elif fmt == "md":
                saved = save_markdown_generic(self._to_markdown(report), filepath)
            else:
                continue
            
            if saved:
                paths[fmt] = saved
                logger.info("Exported: %s", saved)
        
        return {"export_paths": paths}

    def _to_markdown(self, report: Dict[str, str]) -> str:
        """Convert report to markdown."""
        return "\n\n".join(
            f"# {title.replace('_', ' ').title()}\n\n{content}"
            for title, content in report.items()
        )

    # ===============================================================
    # LANGGRAPH WORKFLOW
    # ===============================================================

    def _build_workflow(self):
        """Build linear workflow: generate → export."""
        workflow = StateGraph(WorkflowState)
        workflow.add_node("generate_report", self.generate_report)
        workflow.add_node("export_report", self.export_report)
        
        workflow.add_edge(START, "generate_report")
        workflow.add_edge("generate_report", "export_report")
        workflow.add_edge("export_report", END)
        
        return workflow.compile(checkpointer=MemorySaver())

    # ===============================================================
    # PUBLIC API
    # ===============================================================
    @traceable(name="Phase 2: Generate_and_Compile_Report")
    def compile_report(self, state: WorkflowState) -> WorkflowState:
        """Execute report compilation workflow."""
        from src.utils.create_unique_uuid import generate_uuid
        
        logger.info("Starting report compilation")
        result = self.workflow.invoke(
            state,
            {"configurable": {"thread_id": generate_uuid()}},
        )
        logger.info("Report compilation complete")
        logger.info("📊 Token usage & cost: Check LangSmith dashboard")
        
        return cast(WorkflowState, result)