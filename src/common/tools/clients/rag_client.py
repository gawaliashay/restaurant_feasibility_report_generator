# src\common\tools\clients\rag_client.py

"""
RAG (Retrieval-Augmented Generation) client.
"""

import logging
from typing import Any

from src.configuration.config_loader import config_loader
from src.rag.rag_pipeline import get_rag_pipeline
from ..query_normalizer import normalize_query

logger = logging.getLogger(__name__)


def rag_search(search_query: str | list[str]) -> dict[str, Any]:
    """Retrieve relevant documents from RAG pipeline."""
    # Validate query
    q, error = normalize_query(search_query)
    if error:
        return {
            "tool": "rag",
            "status": "failed",
            "data": [],
            "error": error,
        }
    
    # Execute retrieval
    try:
        pipeline = get_rag_pipeline()
        
        top_k = config_loader.get("rag_retrieval.top_k", 4)
        threshold = config_loader.get("rag_retrieval.score_threshold", 0.3)
        
        chunks = pipeline.retrieve(
            query=q,
            top_k=top_k,
            score_threshold=threshold
        )
        
        results = [
            {
                "text": chunk.text,
                "score": chunk.score,
                "metadata": {
                    "document_name": chunk.metadata.get("document_name"),
                    "chunk_index": chunk.metadata.get("chunk_index"),
                } if chunk.metadata else {},
            }
            for chunk in chunks
        ]
        
        logger.info(f"RAG returned {len(results)} chunks")
        
        return {
            "tool": "rag",
            "status": "success",
            "data": results,
            "error": None,
        }
    
    except Exception as e:
        logger.exception(f"RAG retrieval failed: {e}")
        return {
            "tool": "rag",
            "status": "failed",
            "data": [],
            "error": str(e),
        }