# src\common\tools\clients\serpapi_client.py

"""
SerpAPI client for Google Maps and Google Trends.
"""

import logging
from functools import lru_cache
from typing import Any

import requests

from src.configuration.config_loader import config_loader
from .query_normalizer import normalize_query

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_config() -> dict[str, Any]:
    """Load and cache SerpAPI configuration."""
    return config_loader.get("apis.serpapi", {})


def google_maps(map_query: str | list[str], location: str) -> dict[str, Any]:
    """Search local businesses using Google Maps."""
    # Validate query
    q, error = normalize_query(map_query)
    if error:
        return {
            "tool": "google_maps",
            "status": "failed",
            "data": [],
            "error": error,
        }
    
    # Get configuration
    config = _get_config()
    api_key = config.get("api_key")
    endpoint = config.get("endpoint")
    timeout = config.get("timeout")
    
    if not api_key:
        return {
            "tool": "google_maps",
            "status": "failed",
            "data": [],
            "error": "SerpAPI key is missing",
        }
    
    if not endpoint:
        return {
            "tool": "google_maps",
            "status": "failed",
            "data": [],
            "error": "SerpAPI endpoint is missing",
        }
    
    # Get tool config
    tool_config = config_loader.get("tools.google_maps", {})
    engine = tool_config.get("engine")
    
    if not engine:
        return {
            "tool": "google_maps",
            "status": "failed",
            "data": [],
            "error": "Google Maps engine not configured",
        }
    
    # Build request parameters
    params = {
        "engine": engine,
        "q": q,
        "location": location,
        "hl": "en",
        "gl": "in",
        "api_key": api_key,
    }
    
    # Make API request
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API error
        if data.get("error"):
            return {
                "tool": "google_maps",
                "status": "failed",
                "data": data,
                "error": str(data["error"]),
            }
        
        # Extract local_results
        if isinstance(data, dict) and "local_results" in data:
            return {
                "tool": "google_maps",
                "status": "success",
                "data": data["local_results"],
                "error": None,
            }
        
        return {
            "tool": "google_maps",
            "status": "success",
            "data": [],
            "error": None,
        }
    
    except requests.exceptions.RequestException as e:
        logger.exception(f"Google Maps request failed: {e}")
        return {
            "tool": "google_maps",
            "status": "failed",
            "data": [],
            "error": str(e),
        }
    
    except Exception as e:
        logger.exception(f"Google Maps failed: {e}")
        return {
            "tool": "google_maps",
            "status": "failed",
            "data": [],
            "error": str(e),
        }


def google_trends(trend_query: str | list[str]) -> dict[str, Any]:
    """Get Google Trends data."""
    # Validate query
    q, error = normalize_query(trend_query)
    if error:
        return {
            "tool": "google_trends",
            "status": "failed",
            "data": [],
            "error": error,
        }
    
    # Get configuration
    config = _get_config()
    api_key = config.get("api_key")
    endpoint = config.get("endpoint")
    timeout = config.get("timeout")
    
    if not api_key:
        return {
            "tool": "google_trends",
            "status": "failed",
            "data": [],
            "error": "SerpAPI key is missing",
        }
    
    if not endpoint:
        return {
            "tool": "google_trends",
            "status": "failed",
            "data": [],
            "error": "SerpAPI endpoint is missing",
        }
    
    # Get tool config
    tool_config = config_loader.get("tools.google_trends", {})
    engine = tool_config.get("engine")
    
    if not engine:
        return {
            "tool": "google_trends",
            "status": "failed",
            "data": [],
            "error": "Google Trends engine not configured",
        }
    
    # Build request parameters
    params = {
        "engine": engine,
        "q": q,
        "api_key": api_key,
        **tool_config.get("request_params", {}),
    }
    
    # Make API request
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API error
        if data.get("error"):
            return {
                "tool": "google_trends",
                "status": "failed",
                "data": data,
                "error": str(data["error"]),
            }
        
        # Extract timeline data
        if isinstance(data, dict):
            # Extract from interest_over_time
            if "interest_over_time" in data:
                timeline = data["interest_over_time"].get("timeline_data", [])
                return {
                    "tool": "google_trends",
                    "status": "success",
                    "data": timeline if isinstance(timeline, list) else [],
                    "error": None,
                }
            
            # Extract timeline_data directly
            if "timeline_data" in data:
                timeline = data["timeline_data"]
                return {
                    "tool": "google_trends",
                    "status": "success",
                    "data": timeline if isinstance(timeline, list) else [],
                    "error": None,
                }
            
            # Extract related_queries
            if "related_queries" in data:
                related = data["related_queries"]
                return {
                    "tool": "google_trends",
                    "status": "success",
                    "data": related if isinstance(related, list) else [],
                    "error": None,
                }
        
        return {
            "tool": "google_trends",
            "status": "success",
            "data": [],
            "error": None,
        }
    
    except requests.exceptions.RequestException as e:
        logger.exception(f"Google Trends request failed: {e}")
        return {
            "tool": "google_trends",
            "status": "failed",
            "data": [],
            "error": str(e),
        }
    
    except Exception as e:
        logger.exception(f"Google Trends failed: {e}")
        return {
            "tool": "google_trends",
            "status": "failed",
            "data": [],
            "error": str(e),
        }