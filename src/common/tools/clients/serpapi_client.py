# src/common/tools/clients/serpapi_client.py

"""
SerpAPI client for Google Maps and Google Trends.
"""

from functools import lru_cache
from typing import Any

import requests

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger


@lru_cache(maxsize=1)
def _get_config() -> dict[str, Any]:
    """Load and cache SerpAPI connection settings."""
    return config_loader.get("apis.serpapi", {})


def _failed(tool: str, error: str) -> dict[str, Any]:
    return {"tool": tool, "status": "failed", "data": [], "error": error}


def _ok(tool: str, data: list) -> dict[str, Any]:
    return {"tool": tool, "status": "success", "data": data, "error": None}


def google_maps(query: str, location: str) -> dict[str, Any]:
    """Search local businesses using Google Maps via SerpAPI."""
    if not query or not query.strip():
        return _failed("google_maps", "Query cannot be empty")
    if not location or not location.strip():
        return _failed("google_maps", "Location cannot be empty")

    config = _get_config()
    api_key = config.get("api_key")
    endpoint = config.get("endpoint")
    timeout = config.get("timeout")

    if not api_key:
        return _failed("google_maps", "SerpAPI key is missing")
    if not endpoint:
        return _failed("google_maps", "SerpAPI endpoint is missing")

    params = {
        "engine": "google_local",
        "q": query.strip(),
        "location": location.strip(),
        "hl": "en",
        "gl": "in",
        "api_key": api_key,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            return _failed("google_maps", str(data["error"]))

        if isinstance(data, dict) and "local_results" in data:
            return _ok("google_maps", data["local_results"])

        return _ok("google_maps", [])

    except requests.exceptions.RequestException as e:
        logger.exception("Google Maps request failed", error=str(e))
        return _failed("google_maps", str(e))
    except Exception as e:
        logger.exception("Google Maps failed", error=str(e))
        return _failed("google_maps", str(e))


def google_trends(query: str) -> dict[str, Any]:
    """Get Google Trends data via SerpAPI."""
    if not query or not query.strip():
        return _failed("google_trends", "Query cannot be empty")

    config = _get_config()
    api_key = config.get("api_key")
    endpoint = config.get("endpoint")
    timeout = config.get("timeout")

    if not api_key:
        return _failed("google_trends", "SerpAPI key is missing")
    if not endpoint:
        return _failed("google_trends", "SerpAPI endpoint is missing")

    params = {
        "engine": "google_trends",
        "q": query.strip(),
        "api_key": api_key,
    }

    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            return _failed("google_trends", str(data["error"]))

        if isinstance(data, dict):
            if "interest_over_time" in data:
                timeline = data["interest_over_time"].get("timeline_data", [])
                return _ok("google_trends", timeline if isinstance(timeline, list) else [])

            if "timeline_data" in data:
                timeline = data["timeline_data"]
                return _ok("google_trends", timeline if isinstance(timeline, list) else [])

            if "related_queries" in data:
                related = data["related_queries"]
                return _ok("google_trends", related if isinstance(related, list) else [])

        return _ok("google_trends", [])

    except requests.exceptions.RequestException as e:
        logger.exception("Google Trends request failed", error=str(e))
        return _failed("google_trends", str(e))
    except Exception as e:
        logger.exception("Google Trends failed", error=str(e))
        return _failed("google_trends", str(e))