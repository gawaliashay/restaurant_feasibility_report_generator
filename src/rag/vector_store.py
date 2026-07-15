"""
Vector Store - Qdrant wrapper for restaurant compliance documents
"""

from typing import List, Dict, Any, Optional, Union
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    PayloadSchemaType,
    Condition, 
)
from langchain_qdrant import QdrantVectorStore

from src.logging_exception.logging.logger import logger
from src.configuration.config_loader import config_loader
from src.common.model_loader import model_loader


class ComplianceVectorStore:
    """Qdrant vector store for restaurant compliance documents."""
    
    def __init__(
            self,
            recreate_collection: bool = False,
        ):

        self.config = config_loader.get_all()

        self.vector_config = (
                                self.config.get("rag_vectorstores", {})
                                .get("qdrant", {})
                            )

        self.collection_name = self.vector_config["collection_name"]
        embedding_provider = self.config["rag_embeddings"]["default"]
        self.vector_size = self.config["rag_embeddings"][embedding_provider]["dimensions"]

        self.embeddings = model_loader.get_embeddings()
        self.client = self._init_client()
        self._setup_collection(recreate_collection)
        self.vector_store = self._init_langchain_wrapper()

        logger.info(f"ComplianceVectorStore initialized | Collection: {self.collection_name}")
    
    def _init_client(self) -> QdrantClient:
        return QdrantClient(
            url=self.vector_config["url"],
            api_key=self.vector_config["api_key"],
            timeout=60,
        )
    
    def _setup_collection(self, recreate: bool = False) -> None:
        """Create or recreate collection."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
        except Exception as e:
            logger.error(f"Failed to get collections: {e}")
            exists = False
        
        if recreate and exists:
            logger.info(f"Deleting collection: {self.collection_name}")
            self.client.delete_collection(self.collection_name)
            exists = False
        
        if not exists:
            logger.info(f"Creating collection: {self.collection_name}")           
           
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            self._create_payload_indexes()
    
    def _create_payload_indexes(self) -> None:
        """Create indexes on payload fields."""
        index_fields = ["jurisdiction", "topic", "city", "document_name", "chunk_id", "section"]

        for field in index_fields:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_type=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                pass  # Index may already exist
    
    def _init_langchain_wrapper(self) -> QdrantVectorStore:
        """Initialize LangChain Qdrant wrapper."""
        return QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )
    
    def add_chunks(
            self,
            chunks: List[Dict[str, Any]],
        ) -> List[str]:
        """Add document chunks to vector store with enhanced metadata."""
        if not chunks:
            logger.warning("No chunks to add")
            return []
        
        texts = []
        metadatas = []
        
        for chunk in chunks:
            # Get the text
            texts.append(chunk["text"])
            
            # Get metadata from chunk or use defaults
            original_metadata = chunk.get("metadata", {})
            chunk_index = chunk.get("chunk_index", 0)
            chunk_id = chunk.get("chunk_id", str(uuid.uuid4()))
            document_name = original_metadata.get("document_name", "unknown")
            topic = chunk.get("topic", "General")
            
            # Build metadata with proper extraction
            metadata = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "document_name": document_name,
                "topic": topic,
                "jurisdiction": original_metadata.get("jurisdiction", "Central"),
                "city": original_metadata.get("city", ""),
                "section": original_metadata.get("section", ""),
                "chunk_size": len(chunk["text"]),
                **original_metadata  # Keep any additional metadata
            }
            
            metadatas.append(metadata)
        
        # Add to vector store
        try:
            point_ids = self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas,
            )
            
            # Convert to strings to ensure type safety
            point_ids_str = [str(pid) for pid in point_ids]
            
            logger.info(f"Added {len(chunks)} chunks to {self.collection_name}")
            return point_ids_str
            
        except Exception as e:
            logger.error(f"Failed to add chunks to vector store: {e}")
            raise
    
    def search(
            self,
            query: str,
            top_k: int,
            score_threshold: float,
            jurisdiction: Optional[str] = None,
            topic: Optional[Union[str, List[str]]] = None,
            city: Optional[str] = None,
            document_name: Optional[str] = None,
        ) -> List[Dict[str, Any]]:
    
        """Search for relevant chunks with filters."""
        filter_conditions: List[Condition] = []
        
        if jurisdiction:
            filter_conditions.append(
                FieldCondition(
                    key="jurisdiction",
                    match=MatchValue(value=jurisdiction)
                )
            )
        
        if topic:
            if isinstance(topic, list):
                filter_conditions.append(
                    FieldCondition(
                        key="topic",
                        match=MatchAny(any=topic)
                    )
                )
            else:
                filter_conditions.append(
                    FieldCondition(
                        key="topic",
                        match=MatchValue(value=topic)
                    )
                )
        
        if city:
            filter_conditions.append(
                FieldCondition(
                    key="city",
                    match=MatchValue(value=city)
                )
            )
        
        if document_name:
            filter_conditions.append(
                FieldCondition(
                    key="document_name",
                    match=MatchValue(value=document_name)
                )
            )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=search_filter,
            )
            
            formatted_results = []
            for doc, score in results:
                if score >= score_threshold:
                    metadata = doc.metadata or {}
                    
                    formatted_results.append({
                        'text': doc.page_content,
                        'score': score,
                        'metadata': metadata,
                        'topic': metadata.get('topic'),
                        'jurisdiction': metadata.get('jurisdiction'),
                        'source': metadata.get('document_name'),
                        'section': metadata.get('section'),
                        'chunk_id': metadata.get('chunk_id'),
                        'chunk_index': metadata.get('chunk_index'),
                    })
           
            logger.info(
                        f"SEARCH | query={query} | topic={topic} | jurisdiction={jurisdiction}"
                    )
            
            logger.info(f"Search returned {len(formatted_results)} results for query: {query[:50]}...")
            if formatted_results:
                logger.debug(f"  First result: topic={formatted_results[0]['topic']}, section={formatted_results[0]['section']}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            points_count_result = self.client.count(
                collection_name=self.collection_name,
                exact=True,
            )
            
            points_count = points_count_result.count if points_count_result else 0
            
            vectors_count = points_count
            
            status = "green"
            if hasattr(collection_info, 'status'):
                status = str(collection_info.status)
            
            return {
                'name': self.collection_name,
                'points_count': points_count,
                'vectors_count': vectors_count,
                'status': status,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {'error': str(e)}
    
    def clear_collection(self) -> None:
        """Delete all points in the collection."""
        try:
            self.client.delete_collection(self.collection_name)
            self._setup_collection(recreate=True)
            logger.info(f"Cleared collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")


_vector_store_instance = None


def get_vector_store(
        recreate: bool = False,
    ) -> ComplianceVectorStore:
        global _vector_store_instance
        if _vector_store_instance is None or recreate:
            _vector_store_instance = ComplianceVectorStore(
                recreate_collection=recreate
            )
        return _vector_store_instance


if __name__ == "__main__":
    store = get_vector_store()
    print(store.get_collection_info())
    
    results = store.search(
        query="restaurant license requirements",
        top_k=5,
        score_threshold=0.0,
    )
    print(f"\nResults: {len(results)}")