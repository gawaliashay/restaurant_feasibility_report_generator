# src/common/tools/tool_pipeline.py

"""Validate and run a registered research tool."""

from typing import Any

from src.common.tools.tool_registry import TOOLS
from src.logging_exception.logging.logger import logger


def run_tool(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    logger.info("Executing tool", tool=tool_name)

    tool = TOOLS.get(tool_name)
    if tool is None:
        return {"tool": tool_name, "status": "failed", "data": [], "error": f"Unknown tool: {tool_name}"}

    if error := _validate_params(tool_name, params):
        return {"tool": tool_name, "status": "failed", "data": [], "error": error}

    try:
        response = tool(**params)
        if response.get("status") != "success":
            return {
                "tool": tool_name,
                "status": "failed",
                "data": [],
                "error": response.get("error", "Tool execution failed"),
            }
        logger.info("Tool executed successfully", tool=tool_name)
        return {"tool": tool_name, "status": "success", "data": response.get("data", []), "error": None}
    except Exception as exc:
        logger.exception("Tool execution failed", tool=tool_name)
        return {"tool": tool_name, "status": "failed", "data": [], "error": str(exc)}


def _validate_params(tool_name: str, params: dict[str, Any]) -> str | None:
    query = params.get("query")
    if not isinstance(query, str) or not query.strip():
        return "Missing required parameter: 'query'"
    if tool_name == "google_maps":
        location = params.get("location")
        if not isinstance(location, str) or not location.strip():
            return "Missing required parameter: 'location'"
    return None
