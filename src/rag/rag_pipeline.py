# src/rag/rag_pipeline.py

"""
Reusable RAG retrieval pipeline.

Retrieve chunks. No prompts. No LLM calls.
Truncation lives in the retriever.
"""

from typing import List, Optional

from src.logging_exception.logging.logger import logger
from src.rag.model_schema import RetrievedChunk
from src.rag.retriever.retriever import get_retriever


class RAGPipeline:
    """Thin wrapper around the retriever."""

    def __init__(self):
        self.retriever = get_retriever()
        logger.info("RAGPipeline initialized")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        if not query or not query.strip():
            return []

        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
        )


_rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the singleton RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline