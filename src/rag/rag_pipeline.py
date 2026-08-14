"""
Reusable RAG Pipeline.

Responsibilities:
- Accept a user query.
- Retrieve relevant document chunks.
- Return retrieval results.
- Respect configured limits for token management.

No business logic. No prompt construction. No LLM calls.
"""

from typing import List, Optional

from src.logging_exception.logging.logger import logger
from src.rag.model_schema import RetrievedChunk
from src.rag.retriever.retriever import get_retriever


class RAGPipeline:
    """Simple reusable RAG retrieval pipeline with strict limits."""

    def __init__(self):
        self.retriever = get_retriever()
        logger.info("RAGPipeline initialized")

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        max_chars_per_chunk: int = 500,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant document chunks for a query.
        
        Args:
            query: The search query
            top_k: Number of chunks to retrieve (default from config)
            score_threshold: Minimum similarity score (default from config)
            max_chars_per_chunk: Maximum characters per chunk (default 500)
        
        Returns:
            List of RetrievedChunk objects with truncated text
        """
        if not query or not query.strip():
            return []

        chunks = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        # Truncate text in each chunk to save tokens
        if max_chars_per_chunk > 0:
            for chunk in chunks:
                if len(chunk.text) > max_chars_per_chunk:
                    chunk.text = chunk.text[:max_chars_per_chunk].rstrip() + "..."

        logger.info(f"RAG retrieval completed | chunks={len(chunks)}")
        return chunks


_rag_pipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the singleton RAG pipeline instance."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline