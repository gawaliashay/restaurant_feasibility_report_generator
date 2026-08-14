# src\common\tools\client_connector.py

""" 
External service connectors. 
 
Responsibilities: 
- Call external services. 
- Handle connection-level errors. 
- Return raw service data. 
""" 

import logging 
from functools import lru_cache 
from typing import Any 

import requests 
from langchain_tavily import TavilySearch 

from src.configuration.config_loader import config_loader 
from src.rag.rag_pipeline import get_rag_pipeline 

logger = logging.getLogger(__name__) 


# ============================================================ 
# RESPONSE HELPERS 
# ============================================================ 

def _success(data: Any) -> dict[str, Any]: 
    return { 
        "success": True, 
        "data": data, 
        "error": None, 
    } 


def _failure(error: str, data: Any = None) -> dict[str, Any]: 
    return { 
        "success": False, 
        "data": data, 
        "error": error, 
    } 


def _normalize_query(query: str | list[str]) -> tuple[str, str | None]: 
    """ 
    Normalize query input to a string. 
     
    Handles both string and list inputs. 
     
    Returns: 
        tuple: (normalized_query, error_message) 
               If valid, error_message is None. 
               If invalid, normalized_query is empty string. 
    """ 
    # Handle list input 
    if isinstance(query, list): 
        if not query: 
            return "", "Query list cannot be empty" 
        query = query[0] 
        logger.info(f"Using first query from list: {query}") 
     
    # Validate string 
    if not query or len(query.strip()) < 3: 
        return "", "Query must be at least 3 characters" 
     
    return query.strip(), None 


# ============================================================ 
# TAVILY 
# ============================================================ 

@lru_cache(maxsize=1) 
def _get_tavily_client() -> TavilySearch | None: 
    """Create and cache Tavily client.""" 

    try: 
        api_key = config_loader.get("apis.tavily.api_key") 

        if not api_key: 
            logger.error("Tavily API key is not configured") 
            return None 

        max_results = config_loader.get( 
            "tools.tavily_search.max_results", 
            5, 
        ) 

        return TavilySearch( 
            max_results=max_results, 
            tavily_api_key=api_key, 
        ) 

    except Exception: 
        logger.exception("Failed to initialize Tavily") 
        return None 


def tavily(search_query: str | list[str]) -> dict[str, Any]: 
    """Search the web using Tavily.""" 
     
    # Normalize query (handles string or list) 
    query, error = _normalize_query(search_query) 
    if error: 
        return _failure(error, []) 

    client = _get_tavily_client() 

    if client is None: 
        return _failure("Tavily client unavailable", []) 

    try: 
        response = client.invoke({ 
            "query": query 
        }) 

        if not isinstance(response, dict): 
            return _failure( 
                "Invalid Tavily response", 
                [], 
            ) 

        results = response.get("results", []) 

        if not isinstance(results, list): 
            results = [] 

        logger.info( 
            "Tavily search completed: %s results", 
            len(results), 
        ) 

        return _success(results) 

    except Exception as exc: 
        logger.exception("Tavily search failed") 
        return _failure(str(exc), []) 


# ============================================================ 
# SERPAPI 
# ============================================================ 

@lru_cache(maxsize=1) 
def _get_serpapi_config() -> dict[str, Any]: 
    """Load and cache SerpAPI configuration.""" 

    config = config_loader.get( 
        "apis.serpapi", 
        {}, 
    ) 

    return config if isinstance(config, dict) else {} 


def _call_serpapi( 
    params: dict[str, Any], 
) -> dict[str, Any]: 
    """Execute a SerpAPI request.""" 

    config = _get_serpapi_config() 

    api_key = config.get("api_key") 
    endpoint = config.get("endpoint") 
    timeout = config.get("timeout") 

    if not api_key: 
        return _failure( 
            "SerpAPI API key is not configured" 
        ) 

    if not endpoint: 
        return _failure( 
            "SerpAPI endpoint is not configured" 
        ) 

    try: 
        request_params = { 
            **params, 
            "api_key": api_key, 
        } 

        response = requests.get( 
            endpoint, 
            params=request_params, 
            timeout=timeout, 
        ) 

        response.raise_for_status() 

        data = response.json() 

        if not isinstance(data, dict): 
            return _failure( 
                "Invalid SerpAPI response" 
            ) 

        if data.get("error"): 
            return _failure( 
                str(data["error"]), 
                data, 
            ) 

        return _success(data) 

    except requests.RequestException as exc: 
        logger.exception("SerpAPI request failed") 
        return _failure(str(exc)) 

    except Exception as exc: 
        logger.exception("SerpAPI failed") 
        return _failure(str(exc)) 


# ============================================================ 
# GOOGLE MAPS 
# ============================================================ 

def google_maps( 
    map_query: str | list[str], 
    location: str, 
) -> dict[str, Any]: 
    """Search local businesses through SerpAPI.""" 
     
    # Normalize query (handles string or list) 
    query, error = _normalize_query(map_query) 
    if error: 
        return _failure(error, []) 

    tool_config = config_loader.get( 
        "tools.google_maps", 
        {}, 
    ) 

    # ✅ DO NOT include max_results - it causes 400 error on free plans 
    params = { 
        "engine": tool_config.get("engine"), 
        "q": query, 
        "location": location, 
        "hl": "en", 
        "gl": "in", 
    } 

    if not params["engine"]: 
        return _failure( 
            "Google Maps engine is not configured" 
        ) 

    return _call_serpapi(params) 


# ============================================================ 
# GOOGLE TRENDS 
# ============================================================ 

def google_trends( 
    trend_query: str | list[str], 
) -> dict[str, Any]: 
    """Retrieve Google Trends data through SerpAPI.""" 
     
    # Normalize query (handles string or list) 
    query, error = _normalize_query(trend_query) 
    if error: 
        return _failure(error, []) 

    tool_config = config_loader.get( 
        "tools.google_trends", 
        {}, 
    ) 

    params = { 
        "engine": tool_config.get("engine"), 
        "q": query, 
        **tool_config.get("request_params", {}), 
    } 

    if not params["engine"]: 
        return _failure( 
            "Google Trends engine is not configured" 
        ) 

    return _call_serpapi(params) 


# ============================================================ 
# RAG 
# ============================================================ 

def rag(search_query: str | list[str]) -> dict[str, Any]: 
    """Retrieve relevant documents from RAG.""" 
     
    # Normalize query (handles string or list) 
    query, error = _normalize_query(search_query) 
    if error: 
        return _failure(error, []) 

    try: 
        rag_pipeline = get_rag_pipeline() 

        top_k = config_loader.get( 
            "rag_retrieval.top_k", 
            4, 
        ) 

        score_threshold = config_loader.get( 
            "rag_retrieval.score_threshold", 
            0.3, 
        ) 

        chunks = rag_pipeline.retrieve( 
            query=query, 
            top_k=top_k, 
            score_threshold=score_threshold, 
        ) 

        results = [] 

        for chunk in chunks: 
            results.append({ 
                "text": chunk.text, 
                "score": chunk.score, 
                "metadata": chunk.metadata, 
            }) 

        logger.info( 
            "RAG retrieval completed: %s chunks", 
            len(results), 
        ) 

        return _success(results) 

    except Exception as exc: 
        logger.exception("RAG retrieval failed") 
        return _failure(str(exc), []) 