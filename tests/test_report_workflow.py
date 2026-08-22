"""
Unit tests for ReportWorkflow.
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

from src.workflow.report.report_workflow import ReportWorkflow


class TestReportWorkflow:
    """Test ReportWorkflow functionality."""

    def test_workflow_creates_instance(self):
        """Test that ReportWorkflow can be instantiated."""
        workflow = ReportWorkflow()
        assert workflow is not None
        assert hasattr(workflow, "run")

    @patch("src.workflow.report.report_workflow.ReportSectionRunner")
    @patch("src.workflow.report.report_workflow.config_loader")
    def test_run_workflow(self, mock_config, mock_runner):
        """Test running report workflow."""
        mock_config.get.return_value = {
            "section1": {"enabled": True, "dependencies": []},
            "section2": {"enabled": True, "dependencies": ["section1"]},
        }

        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = {
            "section": "section1",
            "status": "success",
            "report": "Test report",
        }
        mock_runner.return_value = mock_runner_instance

        workflow = ReportWorkflow()
        state = {"section_reports": {}, "errors": []}
        result = workflow.run(state)
        assert result is not None

    @patch("src.workflow.report.report_workflow.config_loader")
    def test_create_node(self, mock_config):
        """Test creating a workflow node."""
        mock_config.get.return_value = {"section1": {"enabled": True, "dependencies": []}}
        workflow = ReportWorkflow()
        node = workflow._create_node("section1")
        assert callable(node)

    @patch("src.workflow.report.report_workflow.ReportSectionRunner")
    @patch("src.workflow.report.report_workflow.config_loader")
    def test_run_with_skipped_sections(self, mock_config, mock_runner):
        """Test running workflow with skipped sections."""
        mock_config.get.return_value = {
            "section1": {"enabled": False, "dependencies": []},
            "section2": {"enabled": True, "dependencies": []},
        }

        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = {
            "section": "section2",
            "status": "success",
            "report": "Test report",
        }
        mock_runner.return_value = mock_runner_instance

        workflow = ReportWorkflow()
        state = {"section_reports": {}, "errors": []}
        result = workflow.run(state)
        assert result is not None

    @patch("src.workflow.report.report_workflow.ReportSectionRunner")
    @patch("src.workflow.report.report_workflow.config_loader")
    def test_run_with_dependencies(self, mock_config, mock_runner):
        """Test running workflow with dependencies."""
        mock_config.get.return_value = {
            "section1": {"enabled": True, "dependencies": []},
            "section2": {"enabled": True, "dependencies": ["section1"]},
            "section3": {"enabled": True, "dependencies": ["section2"]},
        }

        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = {
            "section": "test",
            "status": "success",
            "report": "Test report",
        }
        mock_runner.return_value = mock_runner_instance

        workflow = ReportWorkflow()
        state = {"section_reports": {}, "errors": []}
        result = workflow.run(state)
        assert result is not None

    @patch("src.workflow.report.report_workflow.ReportSectionRunner")
    @patch("src.workflow.report.report_workflow.config_loader")
    def test_run_handles_errors(self, mock_config, mock_runner):
        """Test workflow handles errors gracefully."""
        mock_config.get.return_value = {
            "section1": {"enabled": True, "dependencies": []}
        }

        mock_runner_instance = MagicMock()
        # Return a failure result instead of raising exception
        mock_runner_instance.run.return_value = {
            "section": "section1",
            "status": "failed",
            "error": "Test error",
            "report": "",
        }
        mock_runner.return_value = mock_runner_instance

        workflow = ReportWorkflow()
        state = {"section_reports": {}, "errors": []}
        result = workflow.run(state)
        # Should not raise exception
        assert "section1" in result["section_reports"]
        assert result["section_reports"]["section1"]["status"] == "failed"