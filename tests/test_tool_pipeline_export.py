"""
Manual test for the common tool pipeline.

Run:
    python -m src.common.tools.test_tool_pipeline
"""

import logging
import json
from datetime import datetime
from typing import Any

from src.configuration.config_loader import config_loader
from src.common.tools.tool_pipeline import run_tool, get_available_tools


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


def save_tool_raw_evidence(tool_name: str, result: dict) -> None:
    """Save raw tool data to JSON file."""
    import os
    
    # Create tool_raw_evidence directory
    os.makedirs("reports/raw_evidence/", exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/raw_evidence//{tool_name}_{timestamp}.json"
    
    data = result.get("data", [])
    
    # Save to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"📁 Raw data saved to: {filename}")


def print_full_result(result: dict) -> None:
    """
    Print complete tool result with all details.
    """
    tool_name = result.get("tool", "unknown")
    status = result.get("status", "unknown")
    error = result.get("error")
    data = result.get("data", [])

    print(f"\n🔧 Tool: {tool_name}")
    print(f"📊 Status: {status}")

    if error:
        print(f"❌ Error: {error}")
        return

    if status == "success":
        if isinstance(data, list):
            print(f"📈 Results count: {len(data)}")
            print("\n" + "-" * 50)
            print("FULL RESPONSE:")
            print("-" * 50)
            
            for i, item in enumerate(data[:5]):  # Show only first 5 in console
                print(f"\n--- Result #{i + 1} ---")
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str) and len(value) > 200:
                            print(f"{key}: {value[:200]}...")
                        else:
                            print(f"{key}: {value}")
                else:
                    print(f"Item: {item}")
            
            if len(data) > 5:
                print(f"\n... and {len(data) - 5} more results")
            
            # ✅ Save full raw data to JSON
            save_tool_raw_evidence(tool_name, result)
            
            print("\n" + "-" * 50)
            print("SUMMARY LIST:")
            print("-" * 50)
            for i, item in enumerate(data[:10]):
                if isinstance(item, dict):
                    title = (
                        item.get("title") or
                        item.get("name") or
                        item.get("query") or
                        item.get("text", "").split("\n")[0][:50] or
                        f"Item {i + 1}"
                    )
                    print(f"  {i+1}. {title}")
                else:
                    print(f"  {i+1}. {item}")
            
            if len(data) > 10:
                print(f"  ... and {len(data) - 10} more")

        elif isinstance(data, dict):
            print(f"📊 Data keys: {list(data.keys())}")
            print("\n" + "-" * 50)
            print("FULL RESPONSE:")
            print("-" * 50)
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 200:
                    print(f"{key}: {value[:200]}...")
                elif isinstance(value, list) and len(value) > 10:
                    print(f"{key}: {len(value)} items")
                else:
                    print(f"{key}: {value}")
            
            # ✅ Save full raw data to JSON
            save_tool_raw_evidence(tool_name, result)
        else:
            print(f"📊 Data: {data}")
    else:
        print("No data returned")
    
    print("=" * 70)


def print_summary_result(result: dict) -> None:
    """
    Print a summary of tool result.
    """
    tool_name = result.get("tool", "unknown")
    status = result.get("status", "unknown")
    error = result.get("error")
    data = result.get("data", [])

    print(f"\nTool: {tool_name}")
    print(f"Status: {status}")

    if error:
        print(f"Error: {error}")
        return

    if status == "success":
        if isinstance(data, list):
            print(f"Results count: {len(data)}")
            for i, item in enumerate(data[:5]):
                if isinstance(item, dict):
                    title = (
                        item.get("title") or
                        item.get("name") or
                        item.get("query") or
                        f"Item {i + 1}"
                    )
                    print(f"  - {title}")
            if len(data) > 5:
                print(f"  ... and {len(data) - 5} more")
            
            # ✅ Save full raw data to JSON even in summary mode
            save_tool_raw_evidence(tool_name, result)
        elif isinstance(data, dict):
            print(f"Data keys: {list(data.keys())}")
            save_tool_raw_evidence(tool_name, result)
        else:
            print("Data returned but not in expected format")
    else:
        print("No data returned")


def run_test(tool_name: str, params: dict, full: bool = True) -> None:
    """Run a single tool test and print results."""
    result = run_tool(tool_name, params)
    if full:
        print_full_result(result)
    else:
        print_summary_result(result)


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
    # TEST TAVILY - String Input
    # ============================================================
    print_section("TESTING TAVILY (String Input)")

    params = get_tool_params("tavily_search", context)

    if not params:
        city = location.get("city", "Pune")
        local_area = location.get("local_area", "Baner")
        restaurant = context.get("restaurant_concept", "momo")
        params = {
            "search_query": f"{restaurant} restaurants in {local_area} {city}"
        }

    run_test("tavily_search", params)

    # ============================================================
    # TEST TAVILY - List Input
    # ============================================================
    print_section("TESTING TAVILY (List Input)")

    if params.get("search_query") and isinstance(params["search_query"], str):
        list_params = {"search_query": [params["search_query"]]}
    else:
        list_params = params

    run_test("tavily_search", list_params)

    # ============================================================
    # TEST GOOGLE MAPS
    # ============================================================
    print_section("TESTING GOOGLE MAPS")

    params = get_tool_params("google_maps", context)

    if not params:
        city = location.get("city", "Pune")
        local_area = location.get("local_area", "Baner")
        restaurant = context.get("restaurant_concept", "momo")
        params = {
            "map_query": f"{restaurant} restaurants in {local_area}, {city}",
            "location": f"{city}, {location.get('state', 'Maharashtra')}, {location.get('country', 'India')}"
        }

    run_test("google_maps", params)

    # ============================================================
    # TEST GOOGLE TRENDS
    # ============================================================
    print_section("TESTING GOOGLE TRENDS")

    params = get_tool_params("google_trends", context)

    if not params:
        params = {
            "trend_query": context.get("restaurant_concept", "momo")
        }

    run_test("google_trends", params)

    # ============================================================
    # TEST RAG
    # ============================================================
    print_section("TESTING RAG")

    params = get_tool_params("rag", context)

    if not params:
        params = {
            "search_query": "FSSAI license requirements"
        }

    run_test("rag", params)

    # ============================================================
    # SUMMARY
    # ============================================================
    print_section("ALL TESTS COMPLETED")


if __name__ == "__main__":
    main()