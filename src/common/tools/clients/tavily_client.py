# src\common\tools\clients\tavily_client.py

"""
Tavily web search client.
"""

import logging
from functools import lru_cache
from typing import Any

from langchain_tavily import TavilySearch

from src.configuration.config_loader import config_loader

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> TavilySearch | None:
    """Create and cache Tavily client."""
    try:
        api_key = config_loader.get("apis.tavily.api_key")
        if not api_key:
            logger.error("Tavily API key is not configured")
            return None
        
        max_results = config_loader.get("apis.tavily.max_results", 5)
        return TavilySearch(max_results=max_results, tavily_api_key=api_key)
    
    except Exception as e:
        logger.exception(f"Failed to initialize Tavily: {e}")
        return None


def tavily_search(query: str) -> dict[str, Any]:
    if not query or not query.strip():
        return {"tool": "tavily_search", "status": "failed", "data": [], "error": "Query cannot be empty"}

    client = _get_client()
    if client is None:
        return {"tool": "tavily_search", "status": "failed", "data": [], "error": "Tavily client unavailable"}

    try:
        response = client.invoke({"query": query.strip()})
        results = response.get("results", [])
        return {"tool": "tavily_search", "status": "success", "data": results, "error": None}
    except Exception as e:
        logger.exception("Tavily search failed: %s", e)
        return {"tool": "tavily_search", "status": "failed", "data": [], "error": str(e)}