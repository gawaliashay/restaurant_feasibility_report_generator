# src\common\tools\clients\tavily_client.py

"""
Tavily web search client.
"""

import logging
from functools import lru_cache
from typing import Any

from langchain_tavily import TavilySearch

from src.configuration.config_loader import config_loader
from .query_normalizer import normalize_query

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> TavilySearch | None:
    """Create and cache Tavily client."""
    try:
        api_key = config_loader.get("apis.tavily.api_key")
        if not api_key:
            logger.error("Tavily API key is not configured")
            return None
        
        max_results = config_loader.get("tools.tavily_search.max_results", 5)
        return TavilySearch(max_results=max_results, tavily_api_key=api_key)
    
    except Exception as e:
        logger.exception(f"Failed to initialize Tavily: {e}")
        return None


def tavily_search(search_query: str | list[str]) -> dict[str, Any]:
    """Search the web using Tavily."""
    # Validate query
    q, error = normalize_query(search_query)
    if error:
        return {
            "tool": "tavily",
            "status": "failed",
            "data": [],
            "error": error,
        }
    
    # Get client
    client = _get_client()
    if client is None:
        return {
            "tool": "tavily",
            "status": "failed",
            "data": [],
            "error": "Tavily client unavailable",
        }
    
    # Execute search
    try:
        response = client.invoke({"query": q})
        results = response.get("results", [])
        logger.info(f"Tavily returned {len(results)} results")
        
        return {
            "tool": "tavily",
            "status": "success",
            "data": results,
            "error": None,
        }
    
    except Exception as e:
        logger.exception(f"Tavily search failed: {e}")
        return {
            "tool": "tavily",
            "status": "failed",
            "data": [],
            "error": str(e),
        }