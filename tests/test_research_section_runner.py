"""
Unit tests for ResearchSectionRunner.
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

from src.workflow.research.research_section_runner import ResearchSectionRunner
from src.graph_states.workflow_states import WorkflowState


class TestResearchSectionRunner:
    """Test ResearchSectionRunner functionality."""

    def test_runner_creates_instance(self):
        """Test that ResearchSectionRunner can be instantiated."""
        runner = ResearchSectionRunner()
        assert runner is not None
        assert hasattr(runner, "run")

    def test_run_unknown_section(self):
        """Test running unknown section returns failure."""
        runner = ResearchSectionRunner()
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
        assert "not found" in result["error"].lower()

    @patch("src.workflow.research.research_section_runner.config_loader")
    def test_run_section_not_enabled(self, mock_config):
        """Test running disabled section returns skipped."""
        mock_config.get.return_value = {
            "test_section": {"enabled": False, "tools": [], "queries": {}}
        }
        runner = ResearchSectionRunner()
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

    @patch("src.workflow.research.research_section_runner.run_tool")
    @patch("src.workflow.research.research_section_runner.config_loader")
    def test_run_section_with_tools(self, mock_config, mock_run_tool):
        """Test running section with tools."""
        # Mock config
        mock_config.get.side_effect = lambda key, default=None: {
            "research.sections": {
                "test_section": {
                    "enabled": True,
                    "tools": ["test_tool"],
                    "queries": {"test_tool": ["test query"]},
                }
            },
            "resource_limits.mode": "fast",
            "resource_limits.fast": {"max_evidence_chars_per_section": 1000},
        }.get(key, default)

        # Mock tool result
        mock_run_tool.return_value = {
            "status": "success",
            "data": [{"title": "Test", "content": "Test content"}],
        }

        runner = ResearchSectionRunner()
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
            "section_reports": {},
            "errors": [],
        }
        result = runner.run("test_section", state)
        assert result["status"] == "success"
        assert "evidence" in result


    @patch("src.workflow.research.research_section_runner.run_tool")
    @patch("src.workflow.research.research_section_runner.config_loader")
    def test_run_section_with_tool_failure(self, mock_config, mock_run_tool):
        """Test running section with tool failure."""
        mock_config.get.side_effect = lambda key, default=None: {
            "research.sections": {
                "test_section": {
                    "enabled": True,
                    "tools": ["test_tool"],
                    "queries": {"test_tool": ["test query"]},
                }
            },
            "resource_limits.mode": "fast",
            "resource_limits.fast": {"max_evidence_chars_per_section": 1000},
        }.get(key, default)

        mock_run_tool.return_value = {"status": "failed", "error": "Tool error"}

        runner = ResearchSectionRunner()
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
            "section_reports": {},
            "errors": [],
        }
        result = runner.run("test_section", state)
        # Should still succeed with empty evidence if tool fails
        assert result["status"] == "success"
        assert result["evidence"] == []
        assert result["errors"]
        assert result["errors"][0]["tool"] == "test_tool"