# src\common\tools\tool_pipeline.py

""" 
Common tool execution pipeline. 
 
Responsibilities: 
- Validate tool name. 
- Validate required parameters. 
- Execute the configured connector. 
- Return a standard result. 
""" 

import logging 
from typing import Any, Callable 

from src.common.tools.client_connector import ( 
    google_maps, 
    google_trends, 
    rag, 
    tavily, 
) 
from src.configuration.config_loader import config_loader 

logger = logging.getLogger(__name__) 

ToolFunction = Callable[..., dict[str, Any]] 


# ============================================================ 
# TOOL REGISTRY 
# ============================================================ 

TOOL_REGISTRY: dict[str, ToolFunction] = { 
    "google_maps": google_maps, 
    "tavily_search": tavily, 
    "google_trends": google_trends, 
    "rag": rag, 
} 


# ============================================================ 
# EXECUTION 
# ============================================================ 

def run_tool_pipeline( 
    tool_name: str, 
    params: dict[str, Any], 
) -> dict[str, Any]: 
    """Execute a configured tool.""" 

    logger.info("Tool execution started: %s", tool_name) 

    tool = TOOL_REGISTRY.get(tool_name) 

    if tool is None: 
        return _failure( 
            tool_name, 
            f"Unknown tool: {tool_name}", 
        ) 

    error = _validate_params(tool_name, params) 

    if error: 
        return _failure(tool_name, error) 

    try: 
        response = tool(**params) 

        if not response.get("success"): 
            return _failure( 
                tool_name, 
                response.get("error", "Tool execution failed"), 
            ) 

        logger.info( 
            "Tool execution completed: %s", 
            tool_name, 
        ) 

        return { 
            "tool": tool_name, 
            "status": "success", 
            "data": response.get("data"), 
        } 

    except Exception as exc: 
        logger.exception( 
            "Tool execution failed: %s", 
            tool_name, 
        ) 

        return _failure(tool_name, str(exc)) 


# ============================================================ 
# VALIDATION 
# ============================================================ 

def _validate_params( 
    tool_name: str, 
    params: dict[str, Any], 
) -> str | None: 
    """Validate required parameters from configuration.""" 

    tool_config = config_loader.get( 
        f"tools.{tool_name}", 
        {}, 
    ) 

    if not isinstance(tool_config, dict): 
        return f"Tool configuration not found: {tool_name}" 

    query_parameter = tool_config.get("query_parameter") 

    if not query_parameter: 
        return None 

    value = params.get(query_parameter) 

    if value is None: 
        return ( 
            f"Missing required parameter " 
            f"'{query_parameter}'" 
        ) 

    # Handle string values 
    if isinstance(value, str) and not value.strip(): 
        return ( 
            f"Parameter '{query_parameter}' " 
            f"cannot be empty" 
        ) 

    # Handle list values 
    if isinstance(value, list): 
        if not value: 
            return ( 
                f"Parameter '{query_parameter}' " 
                f"cannot be empty" 
            ) 
        # Check first element 
        if isinstance(value[0], str) and not value[0].strip(): 
            return ( 
                f"Parameter '{query_parameter}' " 
                f"contains empty string" 
            ) 

    # Handle location parameter for google_maps 
    location_param = tool_config.get("location_parameter") 
    if location_param: 
        location_value = params.get(location_param) 
        if isinstance(location_value, str) and not location_value.strip(): 
            return f"Parameter '{location_param}' cannot be empty" 

    return None 


# ============================================================ 
# HELPERS 
# ============================================================ 

def _failure( 
    tool_name: str, 
    error: str, 
) -> dict[str, Any]: 
    return { 
        "tool": tool_name, 
        "status": "failed", 
        "error": error, 
    } 


def get_available_tools() -> list[str]: 
    """Return registered tool names.""" 

    return list(TOOL_REGISTRY) 