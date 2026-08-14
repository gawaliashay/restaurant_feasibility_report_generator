# src/common/tools/test_tool_pipeline.py

"""
Manual test for the common tool pipeline.

Run:
    python -m src.common.tools.test_tool_pipeline
"""

import logging
from typing import Any

from src.configuration.config_loader import config_loader
from src.common.tools.tool_pipeline import run_tool_pipeline, get_available_tools


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def get_business_context() -> dict:
    """Load business context from config."""
    return config_loader.get("business_case.default", {})


def format_template(template: str, context: dict) -> str:
    """
    Format a template string with business context values.
    
    Supports all placeholders from business_case and location.
    """
    location = context.get("location", {})
    
    # Build values dictionary from context
    values = {
        # Business fields
        "restaurant_concept": context.get("restaurant_concept", ""),
        "investment": context.get("investment", ""),
        "target_demographic": context.get("target_demographic", ""),
        "special_note": context.get("special_note", ""),
        # Location fields
        "society": location.get("society", ""),
        "local_area": location.get("local_area", ""),
        "city": location.get("city", ""),
        "state": location.get("state", ""),
        "country": location.get("country", ""),
        "pincode": location.get("pincode", ""),
    }
    
    try:
        return template.format(**values)
    except KeyError as e:
        logging.warning(f"Missing template key: {e}. Using template as-is.")
        return template


def get_tool_params(tool_name: str, context: dict) -> dict:
    """
    Build parameters for a tool based on its config.
    Fully config-driven - no hardcoding.
    """
    tool_config = config_loader.get(f"tools.{tool_name}", {})
    params = {}
    
    # Get query parameter from config
    query_param = tool_config.get("query_parameter")
    if query_param:
        # Check if there are query templates in research config
        # First try research sections, then fallback to tool config
        query_templates = []
        
        # Try to get queries from research sections
        research_sections = config_loader.get("research.sections", {})
        for section_name, section_config in research_sections.items():
            if tool_name in section_config.get("tools", []):
                queries = section_config.get("queries", {}).get(tool_name, [])
                if queries:
                    query_templates.extend(queries)
        
        # If no queries found, try tool config
        if not query_templates:
            query_templates = tool_config.get("queries", [])
        
        # Use first query template if available
        if query_templates:
            formatted_query = format_template(query_templates[0], context)
            params[query_param] = formatted_query
    
    # Get location parameter from config (for google_maps)
    location_param = tool_config.get("location_parameter")
    if location_param:
        location_template = tool_config.get("location_template")
        if location_template:
            params[location_param] = format_template(location_template, context)
    
    return params


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def print_result(result: dict, data_label: str = "Data") -> None:
    """Print formatted tool result."""
    print(f"\nStatus: {result.get('status')}")
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    
    data = result.get('data')
    if data:
        if isinstance(data, dict):
            # For google_maps, show local_results count
            local_results = data.get("local_results", [])
            if local_results:
                print(f"Results count: {len(local_results)}")
            else:
                print(f"{data_label} count: {len(data)}")
        elif isinstance(data, list):
            print(f"{data_label} count: {len(data)}")


def main() -> None:
    # Load business context from config
    context = get_business_context()
    location = context.get("location", {})
    
    print_section("BUSINESS CONTEXT")
    print(f"Restaurant: {context.get('restaurant_concept', 'N/A')}")
    print(f"Location: {location.get('local_area', 'N/A')}, {location.get('city', 'N/A')}, {location.get('state', 'N/A')}")
    print(f"Country: {location.get('country', 'N/A')}")

    print_section("AVAILABLE TOOLS")
    print(get_available_tools())

    # ============================================================
    # TEST TAVILY
    # ============================================================
    print_section("TESTING TAVILY (String Input)")
    
    # Build params from config
    params = get_tool_params("tavily_search", context)
    
    # If no params were built from config, use a fallback
    if not params:
        city = location.get("city", "Pune")
        local_area = location.get("local_area", "Baner")
        restaurant = context.get("restaurant_concept", "momo")
        params = {
            "search_query": f"{restaurant} restaurants in {local_area} {city}"
        }
    
    result = run_tool_pipeline("tavily_search", params)
    print_result(result, "Results")

    print_section("TESTING TAVILY (List Input)")
    
    # Convert query to list if it's a string
    if params.get("search_query") and isinstance(params["search_query"], str):
        list_params = {"search_query": [params["search_query"]]}
    else:
        list_params = params
    
    result = run_tool_pipeline("tavily_search", list_params)
    print_result(result, "Results")

    # ============================================================
    # TEST GOOGLE MAPS
    # ============================================================
    print_section("TESTING GOOGLE MAPS")
    
    # Build params from config
    params = get_tool_params("google_maps", context)
    
    # If no params were built from config, use a fallback
    if not params:
        city = location.get("city", "Pune")
        local_area = location.get("local_area", "Baner")
        restaurant = context.get("restaurant_concept", "momo")
        params = {
            "map_query": f"{restaurant} restaurants in {local_area}, {city}",
            "location": f"{city}, {location.get('state', 'Maharashtra')}, {location.get('country', 'India')}"
        }
    
    result = run_tool_pipeline("google_maps", params)
    print_result(result, "Results")

    # ============================================================
    # TEST GOOGLE TRENDS
    # ============================================================
    print_section("TESTING GOOGLE TRENDS")
    
    # Build params from config
    params = get_tool_params("google_trends", context)
    
    # If no params were built from config, use a fallback
    if not params:
        params = {
            "trend_query": context.get("restaurant_concept", "momo")
        }
    
    result = run_tool_pipeline("google_trends", params)
    print_result(result)

    # ============================================================
    # TEST RAG
    # ============================================================
    print_section("TESTING RAG")
    
    # Build params from config
    params = get_tool_params("rag", context)
    
    # If no params were built from config, use a fallback
    if not params:
        params = {
            "search_query": "FSSAI license requirements"
        }
    
    result = run_tool_pipeline("rag", params)
    print_result(result)


if __name__ == "__main__":
    main()