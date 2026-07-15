"""
Retriever - Pure RAG retrieval interface.
Returns raw chunks only.
All interpretation happens in prompts.yaml.
"""

from dataclasses import dataclass
from typing import List, Optional

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.rag.vector_store import get_vector_store


@dataclass
class RetrievedChunk:
    text: str
    score: float
    topic: str
    source: str
    jurisdiction: str
    section: Optional[str] = None
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None


class DocumentRetriever:
    """
    Pure retrieval layer.

    Responsibilities:
    - Execute vector search
    - Return raw chunks

    Not responsible for:
    - Formatting
    - Compliance extraction
    - Business logic
    - Prompt construction
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.retrieval_config = config_loader.get("rag_retrieval")

        logger.info("DocumentRetriever initialized")

    def retrieve(
            self,
            query: str,
            state: Optional[str] = None,
            topic: Optional[str] = None,
            top_k: Optional[int] = None,
            score_threshold: Optional[float] = None,
        ) -> List[RetrievedChunk]:

        jurisdiction_filter = (
            state
            if self.retrieval_config["jurisdiction_priority"]
            else None
        )

        results = self.vector_store.search(
            query=query,
            top_k=self.retrieval_config["top_k"],
            score_threshold=self.retrieval_config["score_threshold"],
            jurisdiction=jurisdiction_filter,
            topic=topic,
        )

        chunks = [
            RetrievedChunk(
                text=r["text"],
                score=r["score"],
                topic=r["topic"],
                source=r["source"],
                jurisdiction=r["jurisdiction"],
                section=r.get("section"),
                chunk_id=r.get("chunk_id"),
                chunk_index=r.get("chunk_index"),
            )
            for r in results
        ]

        logger.info(
            f"Retrieved {len(chunks)} chunks | query='{query[:50]}'"
        )

        return chunks


_retriever_instance = None


def get_retriever() -> DocumentRetriever:
    global _retriever_instance

    if _retriever_instance is None:
        _retriever_instance = DocumentRetriever()

    return _retriever_instance


if __name__ == "__main__":
    retriever = get_retriever()

    results = retriever.retrieve(
        query="restaurant license requirements"
    )

    print(f"\nFound {len(results)} results")

    for result in results[:3]:
        print(
            f"\nScore: {result.score:.3f}"
            f"\nTopic: {result.topic}"
            f"\nSource: {result.source}"
            f"\nText: {result.text[:150]}..."
        )