"""
Retriever.

Responsibilities:
- Execute semantic search.
- Return RetrievedChunk objects.
- Respect configured limits for token management.

No business logic.
"""

from typing import List, Optional

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.rag.model_schema import RetrievedChunk
from src.rag.vector_store.vector_store import get_vector_store


class Retriever:
    """Retrieve relevant chunks from the vector store with strict limits."""

    def __init__(self):
        retrieval_config = config_loader.get("rag_retrieval", {})
        
        # Default to 4 chunks (reduced from 8 for token management)
        self.top_k = retrieval_config.get("top_k", 4)
        
        # Default score threshold
        self.score_threshold = retrieval_config.get("score_threshold", 0.3)
        
        # Max chars per chunk (for truncation)
        self.max_chars_per_chunk = retrieval_config.get("max_chars_per_chunk", 500)
        
        self.vector_store = get_vector_store()
        
        logger.info(
            "Retriever initialized | top_k=%d | score_threshold=%.2f | max_chars_per_chunk=%d",
            self.top_k,
            self.score_threshold,
            self.max_chars_per_chunk,
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks with limits.
        
        Args:
            query: The search query
            top_k: Number of chunks to retrieve (default from config)
            score_threshold: Minimum similarity score (default from config)
        
        Returns:
            List of RetrievedChunk objects
        """
        # Use provided values or defaults
        effective_top_k = top_k if top_k is not None else self.top_k
        effective_score_threshold = score_threshold if score_threshold is not None else self.score_threshold
        
        # Cap top_k to prevent token explosion
        max_allowed_top_k = 10
        if effective_top_k > max_allowed_top_k:
            logger.warning(
                "top_k=%d exceeds maximum allowed %d, capping",
                effective_top_k,
                max_allowed_top_k,
            )
            effective_top_k = max_allowed_top_k

        # Execute search
        results = self.vector_store.search(
            query=query,
            top_k=effective_top_k,
            score_threshold=effective_score_threshold,
        )

        # Convert to RetrievedChunk objects with truncated text
        chunks = []
        for result in results:
            text = result.get("text", "")
            # Truncate text to save tokens
            if len(text) > self.max_chars_per_chunk:
                text = text[:self.max_chars_per_chunk].rstrip() + "..."
            
            chunks.append(
                RetrievedChunk(
                    text=text,
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata", {}),
                )
            )

        logger.info(
            "RAG retrieval completed | query='%s' | chunks=%d | top_k=%d",
            query[:50] + ("..." if len(query) > 50 else ""),
            len(chunks),
            effective_top_k,
        )
        
        return chunks


_retriever = None


def get_retriever() -> Retriever:
    """Get or create the singleton retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever