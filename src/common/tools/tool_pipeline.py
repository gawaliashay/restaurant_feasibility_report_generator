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
from src.configuration.config_loader import config_loader

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
    """
    Validate required parameters from configuration.

    Returns:
        str | None: Error message if invalid, None if valid.
    """
    tool_config = config_loader.get(f"tools.{tool_name}", {})

    if not isinstance(tool_config, dict):
        return f"Tool configuration not found: {tool_name}"

    # Get required query parameter
    query_param = tool_config.get("query_parameter")

    if not query_param:
        return None

    # Check if parameter exists
    value = params.get(query_param)

    if value is None:
        return f"Missing required parameter: '{query_param}'"

    # Validate string values
    if isinstance(value, str) and not value.strip():
        return f"Parameter '{query_param}' cannot be empty"

    # Validate list values
    if isinstance(value, list):
        if not value:
            return f"Parameter '{query_param}' cannot be empty"
        if isinstance(value[0], str) and not value[0].strip():
            return f"Parameter '{query_param}' contains empty string"

    # Validate location parameter for google_maps
    location_param = tool_config.get("location_parameter")
    if location_param:
        location_value = params.get(location_param)
        if isinstance(location_value, str) and not location_value.strip():
            return f"Parameter '{location_param}' cannot be empty"

    return None


def get_available_tools() -> list[str]:
    """Return list of registered tool names."""
    return list(TOOLS.keys())