"""
Unit tests for ReportSectionRunner.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, MagicMock

from src.workflow.report.report_section_runner import ReportSectionRunner
from src.graph_states.workflow_states import WorkflowState


class TestReportSectionRunner:
    """Test ReportSectionRunner functionality."""

    def test_runner_creates_instance(self):
        """Test that ReportSectionRunner can be instantiated."""
        runner = ReportSectionRunner()
        assert runner is not None
        assert hasattr(runner, "run")

    @patch("src.workflow.report.report_section_runner.config_loader")
    def test_run_unknown_section(self, mock_config):
        """Test running unknown section returns failure."""
        mock_config.get.return_value = {}
        runner = ReportSectionRunner()
        state: WorkflowState = {
            "restaurant_concept": "Test",
            "investment": "₹500,000",
            "target_demographic": "Professionals",
            "special_note": "",
            "society": "",
            "local_area": "",
            "city": "",
            "state": "",
            "country": "",
            "pincode": "",
            "research_results": {},
            "section_reports": {},
            "errors": [],
        }
        result = runner.run("unknown_section", state)
        assert result["status"] == "failed"

    @patch("src.workflow.report.report_section_runner.config_loader")
    def test_run_section_not_enabled(self, mock_config):
        """Test running disabled section returns skipped."""
        mock_config.get.return_value = {
            "test_section": {"enabled": False, "prompt": "test_prompt"}
        }
        runner = ReportSectionRunner()
        state: WorkflowState = {
            "restaurant_concept": "Test",
            "investment": "₹500,000",
            "target_demographic": "Professionals",
            "special_note": "",
            "society": "",
            "local_area": "",
            "city": "",
            "state": "",
            "country": "",
            "pincode": "",
            "research_results": {},
            "section_reports": {},
            "errors": [],
        }
        result = runner.run("test_section", state)
        assert result["status"] == "skipped"

    @patch("src.workflow.report.report_section_runner.config_loader")
    def test_run_section_no_prompt(self, mock_config):
        """Test running section with no prompt returns failure."""
        mock_config.get.return_value = {"test_section": {"enabled": True}}
        runner = ReportSectionRunner()
        state: WorkflowState = {
            "restaurant_concept": "Test",
            "investment": "₹500,000",
            "target_demographic": "Professionals",
            "special_note": "",
            "society": "",
            "local_area": "",
            "city": "",
            "state": "",
            "country": "",
            "pincode": "",
            "research_results": {},
            "section_reports": {},
            "errors": [],
        }
        result = runner.run("test_section", state)
        assert result["status"] == "failed"
        assert "No prompt" in result["error"]


    @patch("src.workflow.report.report_section_runner.prompts_loader")
    @patch("src.workflow.report.report_section_runner.config_loader")
    def test_build_prompt_single_section(self, mock_config, mock_prompts):
        """Test building prompt for single section."""
        mock_prompts.get_prompt.return_value = "Template: {section_insights}"
        mock_config.get.side_effect = lambda key, default=None: {
            "resource_limits.mode": "fast",
            "resource_limits.fast": {
                "max_tool_results_per_section": 10,
                "max_text_per_result": 300,
                "max_evidence_chars_for_final_report": 6000,
            },
            "report.sections": {
                "market_report": {"prompt": "market_analysis_prompt"}
            },
        }.get(key, default)

        runner = ReportSectionRunner()
        state: WorkflowState = {
            "restaurant_concept": "Test",
            "investment": "₹500,000",
            "target_demographic": "Professionals",
            "special_note": "",
            "society": "",
            "local_area": "Test Area",
            "city": "Test City",
            "state": "Test State",
            "country": "Test Country",
            "pincode": "",
            "research_results": {
                "market_analysis": {
                    "evidence": [{"content": "Test evidence", "source": "Test"}]
                }
            },
            "section_reports": {},
            "errors": [],
        }
        prompt, sources = runner._build_prompt(
            {
                "prompt": "market_analysis_prompt",
                "research_section": "market_analysis",
            },
            state,
        )
        assert isinstance(prompt, str)
        assert isinstance(sources, list)

    @patch("src.workflow.report.report_section_runner.prompts_loader")
    @patch("src.workflow.report.report_section_runner.config_loader")
    def test_build_prompt_cross_section(self, mock_config, mock_prompts):
        """Test building prompt for cross-section (risk_assessment)."""
        mock_prompts.get_prompt.return_value = "Template: {section_insights}"
        mock_config.get.side_effect = lambda key, default=None: {
            "resource_limits.mode": "fast",
            "resource_limits.fast": {
                "max_tool_results_cross_section": 25,
                "max_text_per_result": 300,
                "max_evidence_chars_for_final_report": 6000,
            },
            "report.sections": {
                "market_analysis": {"research_section": "market_analysis"},
            },
        }.get(key, default)

        runner = ReportSectionRunner()
        state: WorkflowState = {
            "restaurant_concept": "Test",
            "investment": "₹500,000",
            "target_demographic": "Professionals",
            "special_note": "",
            "society": "",
            "local_area": "Test Area",
            "city": "Test City",
            "state": "Test State",
            "country": "Test Country",
            "pincode": "",
            "research_results": {},
            "section_reports": {
                "market_analysis": {
                    "status": "success",
                    "content": "Draft market content.",
                    "sources": [{"source": "Test Source", "title": "Test Title"}],
                }
            },
            "errors": [],
        }
        prompt, sources = runner._build_prompt(
            {"prompt": "risk_assessment_prompt", "research_section": None},
            state,
        )
        assert isinstance(prompt, str)
        assert isinstance(sources, list)

    def test_format_evidence_empty(self):
        """Test formatting empty evidence."""
        runner = ReportSectionRunner()
        result = runner._format_evidence([], {})
        assert result == "No evidence available."

    def test_format_evidence_with_items(self):
        """Test formatting evidence items."""
        runner = ReportSectionRunner()
        evidence = [
            {
                "tool": "test_tool",
                "source": "Test Source",
                "title": "Test Title",
                "content": "Test content",
                "extra": {"rating": 4.5},
            }
        ]
        limits = {"max_text_per_result": 300, "max_evidence_chars_for_final_report": 6000}
        result = runner._format_evidence(evidence, limits)
        assert "Source: Test Source" in result
        assert "Title: Test Title" in result
        assert "Test content" in result

    def test_get_text_from_response(self):
        """Test extracting text from LLM response."""
        runner = ReportSectionRunner()

        # Test with string response
        result = runner._get_text("Test response")
        assert result == "Test response"

        # Test with object containing content
        class MockResponse:
            content = "Test content"

        result = runner._get_text(MockResponse())
        assert result == "Test content"

        # Test with object containing string content
        result = runner._get_text("")
        assert result == ""