"""
Unit tests for Tool Pipeline.
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

from src.common.tools.tool_pipeline import run_tool, get_available_tools, _validate_params


class TestToolPipeline:
    """Test tool pipeline functionality."""

    def test_get_available_tools(self):
        """Test get_available_tools returns list of tool names."""
        tools = get_available_tools()
        assert isinstance(tools, list)

    def test_run_tool_unknown_tool(self):
        """Test run_tool with unknown tool name."""
        result = run_tool("unknown_tool", {})
        assert result["status"] == "failed"
        assert "Unknown tool" in result["error"]

    @patch("src.common.tools.tool_pipeline.TOOLS")
    def test_run_tool_success(self, mock_tools):
        """Test successful tool execution."""
        mock_tool = MagicMock()
        mock_tool.return_value = {"status": "success", "data": [{"result": "test"}]}
        mock_tools.get.return_value = mock_tool

        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {"query_parameter": "query"}
            result = run_tool("test_tool", {"query": "test"})

        assert result["status"] == "success"
        assert result["data"] == [{"result": "test"}]

    @patch("src.common.tools.tool_pipeline.TOOLS")
    def test_run_tool_failure(self, mock_tools):
        """Test tool execution failure."""
        mock_tool = MagicMock()
        mock_tool.return_value = {"status": "failed", "error": "Tool failed"}
        mock_tools.get.return_value = mock_tool

        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {"query_parameter": "query"}
            result = run_tool("test_tool", {"query": "test"})

        assert result["status"] == "failed"
        assert result["error"] == "Tool failed"

    @patch("src.common.tools.tool_pipeline.TOOLS")
    def test_run_tool_exception(self, mock_tools):
        """Test tool execution exception handling."""
        mock_tool = MagicMock()
        mock_tool.side_effect = Exception("Test exception")
        mock_tools.get.return_value = mock_tool

        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {"query_parameter": "query"}
            result = run_tool("test_tool", {"query": "test"})

        assert result["status"] == "failed"
        assert "Test exception" in result["error"]

    def test_validate_params_missing_config(self):
        """Test parameter validation with missing config."""
        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {}
            error = _validate_params("test_tool", {})
            assert error is None

    def test_validate_params_missing_required_param(self):
        """Test parameter validation with missing required parameter."""
        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {"query_parameter": "required_param"}
            error = _validate_params("test_tool", {})
            assert "Missing required parameter" in error

    def test_validate_params_empty_string(self):
        """Test parameter validation with empty string."""
        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {"query_parameter": "query"}
            error = _validate_params("test_tool", {"query": ""})
            assert "cannot be empty" in error

    def test_validate_params_empty_list(self):
        """Test parameter validation with empty list."""
        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {"query_parameter": "query"}
            error = _validate_params("test_tool", {"query": []})
            assert "cannot be empty" in error

    def test_validate_params_location_empty(self):
        """Test parameter validation with empty location."""
        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {
                "query_parameter": "query",
                "location_parameter": "location",
            }
            error = _validate_params("test_tool", {"query": "test", "location": ""})
            assert "cannot be empty" in error

    def test_validate_params_valid(self):
        """Test parameter validation with valid parameters."""
        with patch("src.common.tools.tool_pipeline.config_loader") as mock_config:
            mock_config.get.return_value = {
                "query_parameter": "query",
                "location_parameter": "location",
            }
            error = _validate_params(
                "test_tool", {"query": "test", "location": "Pune, India"}
            )
            assert error is None