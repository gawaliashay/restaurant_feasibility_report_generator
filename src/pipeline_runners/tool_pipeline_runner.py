"""
Tool pipeline runner - standalone entry point for testing individual tools.

USAGE:
    # Run from project root
    python -m src.pipeline_runners.tool_pipeline_runner --list

    # Run from src/pipeline_runners directory
    cd src/pipeline_runners
    python tool_pipeline_runner.py --list

    # Test a specific tool (uses default query from config)
    python -m src.pipeline_runners.tool_pipeline_runner google_maps
    python -m src.pipeline_runners.tool_pipeline_runner tavily_search
    python -m src.pipeline_runners.tool_pipeline_runner google_trends
    python -m src.pipeline_runners.tool_pipeline_runner rag

    # Test with custom parameters
    python -m src.pipeline_runners.tool_pipeline_runner tavily_search --params '{"search_query": "momo restaurant Pune market"}'

    # Test with location override
    python -m src.pipeline_runners.tool_pipeline_runner google_maps --params '{"map_query": "restaurants in Baner", "location": "Pune, Maharashtra, India"}'

    # Test all tools
    python -m src.pipeline_runners.tool_pipeline_runner --all
"""

import json
import argparse
import sys
from pathlib import Path

# Add project root to path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

from src.common.tools.tool_pipeline import run_tool, get_available_tools
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger


# ============================================================
# HELPERS
# ============================================================

def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_tool_result(result: dict) -> None:
    """Print tool execution result."""
    print(f"Tool: {result.get('tool')}")
    print(f"Status: {result.get('status')}")
    
    data = result.get("data", [])
    if data:
        print(f"Results: {len(data)}")
        for idx, item in enumerate(data[:3]):
            print(f"  {idx+1}. {json.dumps(item, indent=2)[:100]}...")
        if len(data) > 3:
            print(f"  ... and {len(data) - 3} more")
    
    if result.get("error"):
        print(f"Error: {result.get('error')}")


def get_test_query(tool_name: str) -> dict:
    """Get test query for a tool based on config."""
    business = config_loader.get("business_case.default", {})
    location = business.get("location", {})
    
    city = location.get("city", "Pune")
    state = location.get("state", "Maharashtra")
    country = location.get("country", "India")
    local_area = location.get("local_area", "Baner")
    concept = business.get("restaurant_concept", "momo Restaurant")
    
    test_queries = {
        "google_maps": {
            "map_query": f"{concept} in {local_area}, {city}",
            "location": f"{city}, {state}, {country}"
        },
        "google_trends": {
            "trend_query": concept
        },
        "tavily_search": {
            "search_query": f"{concept} market demand trends {city} India"
        },
        "rag": {
            "search_query": "FSSAI registration and license requirements for restaurants"
        }
    }
    
    return test_queries.get(tool_name, {})


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Run individual tool for testing."""
    parser = argparse.ArgumentParser(description="Test individual tools")
    parser.add_argument(
        "tool",
        nargs="?",
        help="Tool name to test"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tools"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all available tools"
    )
    parser.add_argument(
        "--params",
        type=str,
        help="JSON string of parameters (overrides defaults)"
    )
    args = parser.parse_args()

    if args.list:
        print_header("AVAILABLE TOOLS")
        for tool in get_available_tools():
            print(f"  - {tool}")
        print("\nTest a tool: python -m src.pipeline_runners.tool_pipeline_runner <tool_name>")
        return

    if args.all:
        print_header("TESTING ALL TOOLS")
        for tool_name in get_available_tools():
            print(f"\n▶ Testing: {tool_name}")
            params = get_test_query(tool_name)
            result = run_tool(tool_name, params)
            print_tool_result(result)
        return

    if not args.tool:
        parser.print_help()
        print("\nExample: python -m src.pipeline_runners.tool_pipeline_runner tavily_search")
        return

    try:
        tool_name = args.tool
        
        # Validate tool exists
        if tool_name not in get_available_tools():
            print(f"❌ Tool '{tool_name}' not found. Use --list to see available tools.")
            return
        
        # Get parameters
        if args.params:
            params = json.loads(args.params)
        else:
            params = get_test_query(tool_name)
            
        print_header(f"TESTING TOOL: {tool_name}")
        print(f"Params: {json.dumps(params, indent=2)}")

        # Execute tool
        result = run_tool(tool_name, params)
        print_tool_result(result)

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in --params: {e}")
    except Exception as e:
        logger.exception("Tool test failed")
        print(f"\n❌ FAILED: {str(e)}")
        raise


if __name__ == "__main__":
    main()