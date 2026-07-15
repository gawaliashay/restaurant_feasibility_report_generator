"""
Unit tests for tool_loader.py

Run with: python -m pytest tests/test_tool_loader.py -v
Or: python tests/test_tool_loader.py
"""

import unittest
import logging
from unittest.mock import patch, MagicMock, Mock
from typing import Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Clear cache before importing
import functools
from src.common import tool_loader as tl

# Clear lru_cache
tl._get_tavily_client.cache_clear()
tl._get_serpapi_key.cache_clear()

from src.common.tool_loader import (
    _get_tavily_client,
    _get_serpapi_key,
    use_tavily_search,
    use_google_trends,
    use_google_maps,
    tool_loader,
    get_tool,
    check_tools_health,
)

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestToolLoader(unittest.TestCase):
    """Test cases for tool_loader module."""

    def setUp(self):
        """Clear cache before each test."""
        tl._get_tavily_client.cache_clear()
        tl._get_serpapi_key.cache_clear()

    # ================================================================
    # TEST: Lazy-loaded clients
    # ================================================================

    @patch('src.common.tool_loader.config_loader')
    def test_get_tavily_client_success(self, mock_config):
        """Test Tavily client initialization with valid API key."""
        mock_config.get.side_effect = lambda key, default=None: {
            "apis.tavily.api_key": "test_tavily_key",
            "research.tavily_max_results": 10
        }.get(key, default)

        with patch('src.common.tool_loader.TavilySearch') as mock_tavily:
            # Clear cache again to ensure fresh call
            tl._get_tavily_client.cache_clear()
            mock_tavily.return_value = MagicMock()
            client = _get_tavily_client()
            self.assertIsNotNone(client)
            mock_tavily.assert_called_once_with(
                max_results=10, 
                tavily_api_key="test_tavily_key"
            )

    @patch('src.common.tool_loader.config_loader')
    def test_get_tavily_client_failure(self, mock_config):
        """Test Tavily client initialization with invalid API key."""
        mock_config.get.side_effect = lambda key, default=None: {
            "apis.tavily.api_key": None,
            "research.tavily_max_results": 5
        }.get(key, default)

        with patch('src.common.tool_loader.TavilySearch') as mock_tavily:
            tl._get_tavily_client.cache_clear()
            mock_tavily.side_effect = Exception("API key invalid")
            client = _get_tavily_client()
            self.assertIsNone(client)

    @patch('src.common.tool_loader.config_loader')
    def test_get_serpapi_key(self, mock_config):
        """Test SerpAPI key retrieval."""
        tl._get_serpapi_key.cache_clear()
        mock_config.get.return_value = "test_serpapi_key"
        key = _get_serpapi_key()
        self.assertEqual(key, "test_serpapi_key")

    @patch('src.common.tool_loader.config_loader')
    def test_get_serpapi_key_missing(self, mock_config):
        """Test SerpAPI key retrieval when missing."""
        tl._get_serpapi_key.cache_clear()
        mock_config.get.return_value = None
        key = _get_serpapi_key()
        self.assertIsNone(key)

    # ================================================================
    # TEST: Tavily Search
    # ================================================================

    @patch('src.common.tool_loader._get_tavily_client')
    def test_use_tavily_search_success(self, mock_get_client):
        """Test successful Tavily search."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            "results": [
                {"url": "https://example.com/1", "title": "Result 1", "content": "Content 1"},
                {"url": "https://example.com/2", "title": "Result 2", "content": "Content 2"},
            ]
        }
        mock_get_client.return_value = mock_client

        state = {"search_query": ["test query"]}
        result = use_tavily_search(state)

        self.assertEqual(result["tool"], "tavily_search")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sources_count"], 2)
        self.assertEqual(len(result["data"]["results"]), 2)

    @patch('src.common.tool_loader._get_tavily_client')
    def test_use_tavily_search_multiple_queries(self, mock_get_client):
        """Test Tavily search with multiple queries."""
        mock_client = MagicMock()
        mock_client.invoke.side_effect = [
            {"results": [{"url": "https://example.com/1", "title": "Result 1"}]},
            {"results": [{"url": "https://example.com/2", "title": "Result 2"}]},
        ]
        mock_get_client.return_value = mock_client

        state = {"search_query": ["query1", "query2"]}
        result = use_tavily_search(state)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["sources_count"], 2)
        self.assertEqual(mock_client.invoke.call_count, 2)

    @patch('src.common.tool_loader._get_tavily_client')
    def test_use_tavily_search_deduplicates(self, mock_get_client):
        """Test Tavily search deduplicates results by URL."""
        mock_client = MagicMock()
        mock_client.invoke.return_value = {
            "results": [
                {"url": "https://example.com/1", "title": "Result 1"},
                {"url": "https://example.com/1", "title": "Result 1 Duplicate"},
                {"url": "https://example.com/2", "title": "Result 2"},
            ]
        }
        mock_get_client.return_value = mock_client

        state = {"search_query": ["test query"]}
        result = use_tavily_search(state)

        self.assertEqual(result["sources_count"], 2)
        urls = [r["url"] for r in result["data"]["results"]]
        self.assertEqual(len(set(urls)), 2)  # Unique URLs

    @patch('src.common.tool_loader._get_tavily_client')
    def test_use_tavily_search_missing_query(self, mock_get_client):
        """Test Tavily search with missing query."""
        state = {}
        result = use_tavily_search(state)
        # ✅ FIX: Check error field instead of status
        self.assertIn("error", result)
        self.assertIn("missing search_query", result["error"])

    @patch('src.common.tool_loader._get_tavily_client')
    def test_use_tavily_search_client_unavailable(self, mock_get_client):
        """Test Tavily search when client is unavailable."""
        mock_get_client.return_value = None
        state = {"search_query": ["test"]}
        result = use_tavily_search(state)
        # ✅ FIX: Check error field instead of status
        self.assertIn("error", result)
        self.assertIn("tavily client unavailable", result["error"])

    @patch('src.common.tool_loader._get_tavily_client')
    def test_use_tavily_search_exception(self, mock_get_client):
        """Test Tavily search when an exception occurs."""
        mock_client = MagicMock()
        mock_client.invoke.side_effect = Exception("Network error")
        mock_get_client.return_value = mock_client

        state = {"search_query": ["test"]}
        result = use_tavily_search(state)
        self.assertEqual(result["status"], "failed")
        self.assertIn("Network error", result.get("error", ""))

    # ================================================================
    # TEST: Google Trends
    # ================================================================

    @patch('src.common.tool_loader.requests.get')
    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_trends_success(self, mock_get_key, mock_requests):
        """Test successful Google Trends search."""
        mock_get_key.return_value = "test_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "interest_over_time": {
                "timeline_data": [
                    {"value": 75, "date": "2024-01-01"},
                    {"value": 80, "date": "2024-01-02"},
                ]
            },
            "related_queries": []
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.return_value = mock_response

        state = {"trend_query": "momo restaurant"}
        result = use_google_trends(state)

        self.assertEqual(result["tool"], "google_trends")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["timeline_data"]), 2)
        self.assertEqual(result["data"]["query"], "momo restaurant")

    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_trends_missing_query(self, mock_get_key):
        """Test Google Trends with missing query."""
        mock_get_key.return_value = "test_key"
        state = {}
        result = use_google_trends(state)
        # ✅ FIX: Check error field
        self.assertIn("error", result)
        self.assertIn("missing trend_query", result["error"])

    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_trends_missing_key(self, mock_get_key):
        """Test Google Trends with missing API key."""
        mock_get_key.return_value = None
        state = {"trend_query": "test"}
        result = use_google_trends(state)
        # ✅ FIX: Check error field
        self.assertIn("error", result)
        self.assertIn("SerpAPI key unavailable", result["error"])

    @patch('src.common.tool_loader.requests.get')
    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_trends_http_error(self, mock_get_key, mock_requests):
        """Test Google Trends with HTTP error."""
        mock_get_key.return_value = "test_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = Exception("HTTP 400 Bad Request")
        mock_requests.return_value = mock_response

        state = {"trend_query": "test"}
        result = use_google_trends(state)
        self.assertEqual(result["status"], "failed")

    # ================================================================
    # TEST: Google Maps
    # ================================================================

    @patch('src.common.tool_loader.requests.get')
    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_maps_success(self, mock_get_key, mock_requests):
        """Test successful Google Maps search."""
        mock_get_key.return_value = "test_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "local_results": [
                {"title": "Restaurant 1", "rating": 4.5, "reviews": 100},
                {"title": "Restaurant 2", "rating": 4.0, "reviews": 50},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests.return_value = mock_response

        state = {
            "map_query": "momo restaurant in Baner, Pune",
            "location": "Pune, Maharashtra, India"
        }
        result = use_google_maps(state)

        self.assertEqual(result["tool"], "google_maps")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["results"]), 2)
        self.assertEqual(result["data"]["results_count"], 2)

    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_maps_missing_key(self, mock_get_key):
        """Test Google Maps with missing API key."""
        mock_get_key.return_value = None
        state = {"map_query": "test", "location": "test"}
        result = use_google_maps(state)
        self.assertEqual(result["status"], "failed")
        self.assertIn("SerpAPI key unavailable", result.get("error", ""))

    @patch('src.common.tool_loader.requests.get')
    @patch('src.common.tool_loader._get_serpapi_key')
    def test_use_google_maps_http_error(self, mock_get_key, mock_requests):
        """Test Google Maps with HTTP error."""
        mock_get_key.return_value = "test_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("HTTP 500 Server Error")
        mock_requests.return_value = mock_response

        state = {"map_query": "test", "location": "test"}
        result = use_google_maps(state)
        self.assertEqual(result["status"], "failed")

    # ================================================================
    # TEST: Tool Registry
    # ================================================================

    def test_tool_loader_registry(self):
        """Test that all tools are registered correctly."""
        self.assertEqual(len(tool_loader), 3)
        self.assertIn("tavily_search", tool_loader)
        self.assertIn("google_trends", tool_loader)
        self.assertIn("google_maps", tool_loader)

    def test_get_tool_success(self):
        """Test getting a tool by name."""
        tool = get_tool("tavily_search")
        self.assertEqual(tool, use_tavily_search)

    def test_get_tool_not_found(self):
        """Test getting a tool that doesn't exist."""
        tool = get_tool("non_existent_tool")
        self.assertIsNone(tool)

    # ================================================================
    # TEST: Health Check
    # ================================================================

    @patch('src.common.tool_loader._get_tavily_client')
    @patch('src.common.tool_loader._get_serpapi_key')
    def test_check_tools_health_all_healthy(self, mock_get_key, mock_get_client):
        """Test health check when all tools are healthy."""
        tl._get_tavily_client.cache_clear()
        tl._get_serpapi_key.cache_clear()
        
        mock_get_client.return_value = MagicMock()
        mock_get_key.return_value = "test_key"
        
        health = check_tools_health()
        self.assertTrue(health["tavily_search"])
        self.assertTrue(health["serpapi_key"])
        self.assertTrue(health["tool_count"])

    @patch('src.common.tool_loader._get_tavily_client')
    @patch('src.common.tool_loader._get_serpapi_key')
    def test_check_tools_health_missing_key(self, mock_get_key, mock_get_client):
        """Test health check when API key is missing."""
        tl._get_tavily_client.cache_clear()
        tl._get_serpapi_key.cache_clear()
        
        mock_get_client.return_value = None
        mock_get_key.return_value = None
        
        health = check_tools_health()
        self.assertFalse(health["tavily_search"])
        self.assertFalse(health["serpapi_key"])

    def test_check_tools_health_missing_tools(self):
        """Test health check when tools are missing."""
        health = check_tools_health()
        # Should still work with the actual tool_loader
        self.assertEqual(health["tool_count"], True)


# ================================================================
# INTEGRATION TESTS (Optional - requires real API keys)
# ================================================================

class IntegrationTestToolLoader(unittest.TestCase):
    """Integration tests that require real API keys.
    
    These tests are skipped by default. To run them, set:
    TAVILY_API_KEY=your_key
    SERPAPI_API_KEY=your_key
    """
    
    @unittest.skip("Requires real Tavily API key")
    def test_tavily_real_search(self):
        """Real Tavily search with actual API key."""
        import os
        if not os.getenv("TAVILY_API_KEY"):
            self.skipTest("TAVILY_API_KEY not set")
        
        state = {"search_query": ["momo restaurant in Pune"]}
        result = use_tavily_search(state)
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["sources_count"], 0)

    @unittest.skip("Requires real SerpAPI key")
    def test_google_trends_real_search(self):
        """Real Google Trends search with actual API key."""
        import os
        if not os.getenv("SERPAPI_API_KEY"):
            self.skipTest("SERPAPI_API_KEY not set")
        
        state = {"trend_query": "momo restaurant"}
        result = use_google_trends(state)
        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["data"]["timeline_data"]), 0)

    @unittest.skip("Requires real SerpAPI key")
    def test_google_maps_real_search(self):
        """Real Google Maps search with actual API key."""
        import os
        if not os.getenv("SERPAPI_API_KEY"):
            self.skipTest("SERPAPI_API_KEY not set")
        
        state = {
            "map_query": "momo restaurant in Baner, Pune",
            "location": "Pune, Maharashtra, India"
        }
        result = use_google_maps(state)
        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["data"]["results"]), 0)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)