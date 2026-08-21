"""
Registry of available research tools.
"""

from src.common.tools.clients.tavily_client import tavily_search
from src.common.tools.clients.serpapi_client import google_maps, google_trends
from src.common.tools.clients.rag_client import rag_search


TOOLS = {
    "tavily_search": tavily_search,
    "google_maps": google_maps,
    "google_trends": google_trends,
    "rag": rag_search,
}