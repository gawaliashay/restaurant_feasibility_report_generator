import logging
from typing import Dict, Any, Optional
from functools import lru_cache

import requests
from langchain_tavily import TavilySearch

from src.configuration.config_loader import config_loader
from src.rag.rag_query_pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Lazy-loaded clients
# ---------------------------------------------------------------------
@lru_cache(maxsize=1)
def _get_tavily_client() -> Optional[TavilySearch]:
    try:
        api_key = config_loader.get("apis.tavily.api_key")
        max_results = config_loader.get("research.tavily_max_results", 5)
        return TavilySearch(max_results=max_results, tavily_api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Tavily: {e}")
        return None


@lru_cache(maxsize=1)
def _get_serpapi_key() -> Optional[str]:
    return config_loader.get("apis.serpapi.api_key")


# ---------------------------------------------------------------------
# Helper to get tool config
# ---------------------------------------------------------------------
def _get_tool_config(tool_name: str) -> Dict[str, Any]:
    """Get tool configuration from configs.yaml."""
    return config_loader.get("tools", {}).get(tool_name, {})


# ---------------------------------------------------------------------
# Tool Functions - Each tool returns its own summary with config caps
# ---------------------------------------------------------------------
def use_tavily_search(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Tavily web search."""
    queries = state.get("search_query")
    logger.info(f"Tavily query: {queries}")
    if not queries:
        return {"tool": "tavily_search", "error": "missing search_query", "status": "failed"}

    client = _get_tavily_client()
    if not client:
        return {"tool": "tavily_search", "error": "tavily client unavailable", "status": "failed"}

    try:
        all_results = []
        for query in queries:
            result = client.invoke({"query": query})
            seen_urls = set()
            for item in result.get("results", []):
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(item)

        # ✅ Get cap from tool config
        tool_config = _get_tool_config("tavily_search")
        max_results = tool_config.get("max_results", 15)
        all_results = all_results[:max_results]

        logger.info(f"Tavily returned {len(all_results)} results (cap: {max_results})")
        
        # Generate summary
        insights = []
        for r in all_results[:8]:
            title = r.get("title", "Unknown")
            content = r.get("content", r.get("snippet", ""))
            insights.append(f"- {title}: {content}" if content else f"- {title}")
        summary = f"Market Insights ({len(all_results)} results):\n" + "\n".join(insights)
        
        return {
            "tool": "tavily_search",
            "status": "success",
            "data": {
                "queries": queries,
                "results": all_results
            },
            "sources_count": len(all_results),
            "summary": summary
        }
    except Exception as e:
        logger.exception(f"Tavily search failed: {e}")
        return {"tool": "tavily_search", "error": str(e), "status": "failed"}


def use_google_trends(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Google Trends search via SerpAPI."""
    query = state.get("trend_query")
    if not query:
        return {"tool": "google_trends", "error": "missing trend_query", "status": "failed"}

    api_key = _get_serpapi_key()
    if not api_key:
        return {"tool": "google_trends", "error": "SerpAPI key unavailable", "status": "failed"}

    params = {
        "engine": "google_trends",
        "q": query,
        "api_key": api_key,
        "data_type": "TIMESERIES"
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        timeline_data = data.get("interest_over_time", {}).get("timeline_data", [])

        # ✅ Get cap from tool config
        tool_config = _get_tool_config("google_trends")
        max_points = tool_config.get("max_points", 20)
        timeline_data = timeline_data[:max_points]

        logger.info(f"Google Trends returned {len(timeline_data)} points (cap: {max_points})")
        
        # Generate summary
        values = []
        for point in timeline_data[:20]:
            try:
                v = point.get("values", [{}])[0].get("extracted_value", 0)
                if v:
                    values.append(v)
            except (IndexError, KeyError, TypeError):
                continue
        
        if values:
            avg = sum(values) // len(values)
            peak = max(values)
            current = values[-1]
            summary = f"Average: {avg}/100 | Peak: {peak}/100 | Current: {current}/100"
        else:
            summary = "No trend data available."
        
        return {
            "tool": "google_trends",
            "status": "success",
            "data": {
                "query": query,
                "timeline_data": timeline_data,
                "related_queries": data.get("related_queries", [])
            },
            "summary": summary
        }
    except Exception as e:
        logger.exception(f"Google Trends failed: {e}")
        return {"tool": "google_trends", "error": str(e), "status": "failed"}


def use_google_maps(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Google Maps search for competitor analysis."""
    logger.info("Google Maps query=%s location=%s", state.get("map_query"), state.get("location"))
    try:
        api_key = _get_serpapi_key()
        if not api_key:
            return {"tool": "google_maps", "error": "SerpAPI key unavailable", "status": "failed"}

        query = state.get("map_query")
        location = state.get("location")

        params = {
            "engine": "google_local",
            "q": query,
            "location": location,
            "hl": "en",
            "gl": "in",
            "api_key": api_key
        }
        
        logger.info(f"Searching Google Maps: {query}")
        response = requests.get("https://serpapi.com/search", params=params, timeout=60)
        if response.status_code != 200:
            logger.error(response.text)
        response.raise_for_status()

        results = response.json()
        local_results = results.get("local_results", [])

        # ✅ Get cap from tool config
        tool_config = _get_tool_config("google_maps")
        max_results = tool_config.get("max_results", 15)
        local_results = local_results[:max_results]

        logger.info(f"Google Maps returned {len(local_results)} results (cap: {max_results})")
        
        # Generate summary
        competitors = []
        for r in local_results:
            name = r.get('title', 'Unknown')
            rating = r.get('rating', 'N/A')
            reviews = r.get('reviews', '0')
            price = r.get('price', 'N/A')
            competitors.append(f"Competitor: {name} | Rating: {rating} | Reviews: {reviews} | Price: {price}")
        
        ratings = [float(r.get('rating', 0)) for r in local_results if r.get('rating')]
        avg = round(sum(ratings) / len(ratings), 1) if ratings else "N/A"
        summary = f"Total: {len(local_results)} | Avg Rating: {avg}\n" + "\n".join(competitors)

        return {
            "tool": "google_maps",
            "status": "success",
            "data": {
                "results": local_results,
                "results_count": len(local_results)
            },
            "summary": summary
        }
    except Exception as e:
        logger.exception(f"Google Maps failed: {e}")
        return {"tool": "google_maps", "error": str(e), "status": "failed"}


def use_rag(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute RAG query - handles its own summarization."""
    queries = state.get("search_query", [])
    if not queries:
        return {"tool": "rag", "error": "missing search_query", "status": "failed"}
    
    try:
        rag = get_rag_pipeline()
        all_chunks = []

        tool_config = _get_tool_config("rag")
        max_chunks = tool_config.get("max_results", 8)
        
        for query in queries:
            # ✅ Just use query - it already has location
            result = rag.query(query=query)
            chunks = result.get("raw_chunks", [])
            if chunks:
                all_chunks.extend(chunks)
        
        # Deduplicate
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            key = f"{chunk.get('source', '')}_{chunk.get('text', '')[:100]}"
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)
        
        unique_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        limited_chunks = unique_chunks[:max_chunks]
        
        logger.info(f"RAG returned {len(limited_chunks)} chunks (cap: {max_chunks})")
        
        if limited_chunks:
            insights = []
            for chunk in limited_chunks:
                text = chunk.get("text", "")
                source = chunk.get("source", "Unknown")
                if text:
                    insights.append(f"Compliance ({source}): {text}")
            summary = f"Compliance Requirements ({len(limited_chunks)} chunks):\n" + "\n\n".join(insights)
        else:
            summary = "No compliance data found."
        
        return {
            "tool": "rag",
            "status": "success",
            "data": {
                "raw_chunks": limited_chunks,
                "total_chunks": len(limited_chunks)
            },
            "summary": summary
        }
    except Exception as e:
        logger.exception("RAG failed")
        return {"tool": "rag", "error": str(e), "status": "failed"}

# ---------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------
tool_loader = {
    "tavily_search": use_tavily_search,
    "google_trends": use_google_trends,
    "google_maps": use_google_maps,
    "rag": use_rag,
}


def get_tool(tool_name: str):
    """Get tool function by name."""
    return tool_loader.get(tool_name)


def check_tools_health() -> Dict[str, bool]:
    """Check if all tools are properly configured."""
    return {
        "tavily_search": _get_tavily_client() is not None,
        "serpapi_key": _get_serpapi_key() is not None,
        "rag": True,
        "tool_count": len(tool_loader) == 4,
    }