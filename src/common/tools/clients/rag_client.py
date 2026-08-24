# src\common\tools\clients\rag_client.py

"""
RAG (Retrieval-Augmented Generation) client.
"""

import logging
from typing import Any

from src.configuration.config_loader import config_loader
from src.rag.rag_pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)


def rag_search(query: str) -> dict[str, Any]:
    if not query or not query.strip():
        return {"tool": "rag", "status": "failed", "data": [], "error": "Query cannot be empty"}

    try:
        pipeline = get_rag_pipeline()
        top_k = config_loader.get("rag_retrieval.top_k", 4)
        threshold = config_loader.get("rag_retrieval.score_threshold", 0.3)
        chunks = pipeline.retrieve(
            query=query.strip(),
            top_k=top_k,
            score_threshold=threshold,
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
        return {"tool": "rag", "status": "success", "data": results, "error": None}
    except Exception as e:
        logger.exception("RAG retrieval failed: %s", e)
        return {"tool": "rag", "status": "failed", "data": [], "error": str(e)}