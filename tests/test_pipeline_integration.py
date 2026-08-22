"""
Integration tests for full pipeline.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    def test_build_state_has_required_fields(self):
        """Test that build_state creates valid WorkflowState."""
        from src.pipeline_runners.pipeline import build_state

        state = build_state()
        assert isinstance(state, dict)
        assert "restaurant_concept" in state
        assert "local_area" in state
        assert "city" in state
        assert "research_results" in state
        assert "section_reports" in state
        assert "errors" in state

    def test_research_workflow_imports(self):
        """Test that research workflow imports correctly."""
        from src.workflow.research.research_workflow import ResearchWorkflow
        from src.workflow.research.research_section_runner import ResearchSectionRunner

        assert ResearchWorkflow is not None
        assert ResearchSectionRunner is not None

    def test_report_workflow_imports(self):
        """Test that report workflow imports correctly."""
        from src.workflow.report.report_workflow import ReportWorkflow
        from src.workflow.report.report_section_runner import ReportSectionRunner
        from src.workflow.report.report_compiler import ReportCompiler
        from src.workflow.report.report_exporter import export_report

        assert ReportWorkflow is not None
        assert ReportSectionRunner is not None
        assert ReportCompiler is not None
        assert export_report is not None

    def test_model_loader_imports(self):
        """Test that model loader imports correctly."""
        from src.common.model_loader import model_loader

        assert model_loader is not None
        assert hasattr(model_loader, "get_llm")

    def test_config_loader_imports(self):
        """Test that config loader imports correctly."""
        from src.configuration.config_loader import config_loader

        assert config_loader is not None
        assert hasattr(config_loader, "get")

    def test_prompts_loader_imports(self):
        """Test that prompts loader imports correctly."""
        from src.configuration.prompts_loader import prompts_loader

        assert prompts_loader is not None
        assert hasattr(prompts_loader, "get_prompt")

    def test_evidence_processor_imports(self):
        """Test that evidence processor imports correctly."""
        from src.common.tools.evidence_processor import EvidenceProcessor

        processor = EvidenceProcessor()
        assert processor is not None
        assert hasattr(processor, "process")

    def test_tool_pipeline_imports(self):
        """Test that tool pipeline imports correctly."""
        from src.common.tools.tool_pipeline import run_tool, get_available_tools

        assert run_tool is not None
        assert get_available_tools is not None

    def test_pipeline_runners_imports(self):
        """Test that pipeline runners import correctly."""
        from src.pipeline_runners.pipeline import main as pipeline_main
        from src.pipeline_runners.research_pipeline_runner import main as research_main
        from src.pipeline_runners.report_pipeline_runner import main as report_main

        assert pipeline_main is not None
        assert research_main is not None
        assert report_main is not None

    def test_report_compiler_imports(self):
        """Test that report compiler imports correctly."""
        from src.workflow.report.report_compiler import ReportCompiler

        compiler = ReportCompiler()
        assert compiler is not None
        assert hasattr(compiler, "compile")

    def test_resource_limits_imports(self):
        """Test that resource limits can be loaded."""
        from src.configuration.config_loader import config_loader

        mode = config_loader.get("resource_limits.mode", "balanced")
        assert mode in ["fast", "balanced", "quality"]