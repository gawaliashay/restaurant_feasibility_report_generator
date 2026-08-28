"""
Unit tests for Tool Pipeline.
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from unittest.mock import MagicMock, patch

from src.common.tools.tool_registry import TOOLS
from src.common.tools.tool_pipeline import _validate_params, run_tool


class TestToolPipeline:
    def test_get_available_tools(self):
        tools = list(TOOLS.keys())
        assert isinstance(tools, list)

    def test_run_tool_unknown_tool(self):
        result = run_tool("unknown_tool", {})
        assert result["status"] == "failed"
        assert "Unknown tool" in result["error"]

    @patch("src.common.tools.tool_pipeline.TOOLS")
    def test_run_tool_success(self, mock_tools):
        mock_tool = MagicMock()
        mock_tool.return_value = {"status": "success", "data": [{"result": "test"}]}
        mock_tools.get.return_value = mock_tool

        result = run_tool("test_tool", {"query": "test"})

        assert result["status"] == "success"
        assert result["data"] == [{"result": "test"}]

    @patch("src.common.tools.tool_pipeline.TOOLS")
    def test_run_tool_failure(self, mock_tools):
        mock_tool = MagicMock()
        mock_tool.return_value = {"status": "failed", "error": "Tool failed"}
        mock_tools.get.return_value = mock_tool

        result = run_tool("test_tool", {"query": "test"})

        assert result["status"] == "failed"
        assert result["error"] == "Tool failed"

    @patch("src.common.tools.tool_pipeline.TOOLS")
    def test_run_tool_exception(self, mock_tools):
        mock_tool = MagicMock()
        mock_tool.side_effect = Exception("Test exception")
        mock_tools.get.return_value = mock_tool

        result = run_tool("test_tool", {"query": "test"})

        assert result["status"] == "failed"
        assert "Test exception" in result["error"]

    def test_validate_params_missing_query(self):
        error = _validate_params("tavily_search", {})
        assert error == "Missing required parameter: 'query'"

    def test_validate_params_empty_query(self):
        error = _validate_params("tavily_search", {"query": ""})
        assert error == "Missing required parameter: 'query'"

    def test_validate_params_maps_missing_location(self):
        error = _validate_params("google_maps", {"query": "restaurants in Baner"})
        assert error == "Missing required parameter: 'location'"

    def test_validate_params_maps_empty_location(self):
        error = _validate_params("google_maps", {"query": "restaurants in Baner", "location": ""})
        assert error == "Missing required parameter: 'location'"

    def test_validate_params_maps_valid(self):
        error = _validate_params(
            "google_maps",
            {"query": "restaurants in Baner", "location": "Pune, Maharashtra, India"},
        )
        assert error is None