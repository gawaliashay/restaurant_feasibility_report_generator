# src/common/tool_loader.py

import logging
import requests
from typing import Dict, Any

from langchain_tavily import TavilySearch
from src.configuration.config_loader import config_loader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Load config once
# ---------------------------------------------------------------------
try:
    config = config_loader.get()
except Exception as e:
    logger.exception("Failed to load configuration.")
    raise

# ---------------------------------------------------------------------
# Initialize Tavily Search
# ---------------------------------------------------------------------
try:
    tavily_search = TavilySearch(
        max_results=config['research'].get('tavily_max_results', 5),
        tavily_api_key=config['apis']['tavily']['api_key']
    )
except Exception as e:
    logger.exception("Failed to initialize TavilySearch.")
    tavily_search = None

# SerpAPI key
SERPAPI_API_KEY = config['apis']['serpapi'].get('api_key')


# ---------------------------------------------------------------------
# Tavily Search
# ---------------------------------------------------------------------
def use_tavily_search(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("search_query")
    if not query:
        return {"error": "missing search_query"}

    if tavily_search is None:
        return {"error": "tavily client initialization failed"}

    try:
        results = tavily_search.invoke({"query": query})
        return {
            "tool": "tavily_search",
            "results": results,
            "sources_count": len(results),
        }
    except Exception as e:
        logger.exception("Tavily search failed.")
        return {"error": f"tavily search failed: {e}"}


# ---------------------------------------------------------------------
# Google Trends via SerpAPI
# ---------------------------------------------------------------------
def use_google_trends(state: Dict[str, Any]) -> Dict[str, Any]:
    query = state.get("trend_query")
    if not query:
        return {"error": "missing trend_query"}

    params = {
        "engine": "google_trends",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "data_type": "TIMESERIES"
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=20)
        response.raise_for_status()

        data = response.json()
        return {
            "tool": "google_trends",
            "query": query,
            "data": data.get("interest_over_time", {}),
            "related_queries": data.get("related_queries", []),
            "sources_count": 1,
        }
    except Exception as e:
        logger.exception("Google Trends request failed.")
        return {"error": f"google trends failed: {e}"}


# ---------------------------------------------------------------------
# Google Maps (via SerpAPI — competitors lookup)
# ---------------------------------------------------------------------
def use_google_maps(state: Dict) -> Dict:
    """Google Maps for restaurant competition analysis"""
    try:
        # Get config
        config = config_loader.get()
        tool_config = config['tools']['google_maps']
        business_config = config['business_case']['default']
        
        # Get location from state or config
        location_data = state.get("location", {})
        if isinstance(location_data, dict):
            city = location_data.get("city", business_config['location']['city'])
            state_name = location_data.get("state", business_config['location']['state'])
        else:
            city = business_config['location']['city']
            state_name = business_config['location']['state']
        
        location = f"{city}, {state_name}, India"
        
        # Build query from config template
        query_template = tool_config['parameters']['query']['template']
        query_context = {
            "restaurant_concept": state.get("restaurant_concept", business_config['restaurant_concept']),
            "city": city
        }
        query = query_template.format(**query_context)
        
        params = {
            "engine": "google_local",
            "q": query,
            "location": location,
            "hl": "en", 
            "gl": "in",
            "api_key": SERPAPI_API_KEY
        }
        
        logger.info(f"Searching Google Maps for {query} in {location}...")
        response = requests.get("https://serpapi.com/search", params=params, timeout=20)
        response.raise_for_status()
        
        results = response.json()
        local_results = results.get("local_results", [])
        
        return {
            "tool": "google_maps",
            "results": local_results,
            "results_count": len(local_results),
            "status": "success"
        }
            
    except Exception as e:
        logger.exception("Google Maps request failed.")
        return {"error": f"Google Maps failed: {str(e)}"}

# ---------------------------------------------------------------------
# SerpAPI Key Check
# ---------------------------------------------------------------------
def check_serpapi_key() -> bool:
    if not SERPAPI_API_KEY or SERPAPI_API_KEY.startswith("${"):
        logger.error("SERPAPI_API_KEY not configured.")
        return False
    return True


# ---------------------------------------------------------------------
# Tool mapping for LangGraph
# ---------------------------------------------------------------------
tool_loader = {
    "tavily_search": use_tavily_search,
    "google_trends": use_google_trends,
    "google_maps": use_google_maps,
}