# src\rag\vector_store\vector_store.py

"""
Reusable Qdrant Vector Store.

Responsibilities:
- Manage Qdrant collection
- Store document chunks
- Perform similarity search

No business logic.
"""

from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.common.model_loader import model_loader
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger


class VectorStore:
    """Simple wrapper around Qdrant."""

    def __init__(self, recreate: bool = False) -> None:
        vector_config = config_loader.get("rag_vectorstores", {}).get("qdrant", {})
        embedding_config = config_loader.get("rag_embeddings", {}).get("openai", {})

        self.collection_name = vector_config["collection_name"]
        self.vector_size = embedding_config["dimensions"]

        self.embeddings = model_loader.get_embeddings()

        self.client = QdrantClient(
            url=vector_config["url"],
            api_key=vector_config.get("api_key"),
            timeout=60,
        )

        if recreate:
            self._recreate_collection()
        else:
            self._ensure_collection()

        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

        logger.info(f"VectorStore initialized: {self.collection_name}")

    def _ensure_collection(self) -> None:
        """Create collection if it does not exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if exists:
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Created collection: {self.collection_name}")

    def _recreate_collection(self) -> None:
        """Delete and recreate collection."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Recreated collection: {self.collection_name}")

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Store document chunks.

        Expected format:
        {
            "text": "...",
            "metadata": {...}
        }
        """
        if not chunks:
            return []

        documents = [
            Document(page_content=chunk["text"], metadata=chunk.get("metadata", {}))
            for chunk in chunks
        ]

        ids = self.vector_store.add_documents(documents)
        logger.info(f"Stored {len(ids)} chunks")
        return [str(point_id) for point_id in ids]

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search."""
        results = self.vector_store.similarity_search_with_score(query=query, k=top_k)

        output = []
        for document, score in results:
            if score < score_threshold:
                continue
            output.append({
                "text": document.page_content,
                "score": score,
                "metadata": document.metadata,
            })

        logger.info(f"Search returned {len(output)} chunks")
        return output

    def get_collection_info(self) -> Dict[str, Any]:
        info = self.client.get_collection(self.collection_name)
        count = self.client.count(collection_name=self.collection_name, exact=True)
        return {
            "collection_name": self.collection_name,
            "points": count.count,
            "status": str(info.status),
        }


_vector_store = None


def get_vector_store(recreate: bool = False) -> VectorStore:
    global _vector_store
    if _vector_store is None or recreate:
        _vector_store = VectorStore(recreate=recreate)
    return _vector_store