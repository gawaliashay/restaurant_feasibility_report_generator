# src\common\tools\tool_pipeline.py

"""
Common tool execution pipeline.

Responsibilities:
- Validate tool name exists
- Validate required parameters
- Execute the tool
- Return standardized response
"""

import logging
from typing import Any

from src.common.tools.tool_registry import TOOLS

logger = logging.getLogger(__name__)


def run_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a tool with validation.

    Args:
        tool_name: Name of the tool to execute
        params: Parameters for the tool

    Returns:
        Standardized response: {tool, status, data, error}
    """
    logger.info(f"Executing tool: {tool_name}")

    # Step 1: Check if tool exists
    tool = TOOLS.get(tool_name)
    if tool is None:
        return {
            "tool": tool_name,
            "status": "failed",
            "data": [],
            "error": f"Unknown tool: {tool_name}",
        }

    # Step 2: Validate parameters
    error = _validate_params(tool_name, params)
    if error:
        return {
            "tool": tool_name,
            "status": "failed",
            "data": [],
            "error": error,
        }

    # Step 3: Execute tool
    try:
        response = tool(**params)

        if response.get("status") != "success":
            return {
                "tool": tool_name,
                "status": "failed",
                "data": [],
                "error": response.get("error", "Tool execution failed"),
            }

        logger.info(f"Tool executed successfully: {tool_name}")

        return {
            "tool": tool_name,
            "status": "success",
            "data": response.get("data", []),
            "error": None,
        }

    except Exception as e:
        logger.exception(f"Tool execution failed: {tool_name}")
        return {
            "tool": tool_name,
            "status": "failed",
            "data": [],
            "error": str(e),
        }


def _validate_params(tool_name: str, params: dict[str, Any]) -> str | None:
    query = params.get("query")
    if not isinstance(query, str) or not query.strip():
        return "Missing required parameter: 'query'"

    if tool_name == "google_maps":
        location = params.get("location")
        if not isinstance(location, str) or not location.strip():
            return "Missing required parameter: 'location'"

    return None


def get_available_tools() -> list[str]:
    """Return list of registered tool names."""
    return list(TOOLS.keys())