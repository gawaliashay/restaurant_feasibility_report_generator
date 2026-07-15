# src\rag\rag_query_pipeline.py

"""
RAG Pipeline - Pure retrieval, NO parsing or extraction
All interpretation happens in prompts.yaml
All limits from rag_retrieval config
"""

from typing import List, Dict, Any, Optional
from src.rag.retriever import DocumentRetriever
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger


class RAGPipeline:
    """
    Pure RAG pipeline - returns raw data only.
    No license extraction, no answer parsing, no hardcoded logic.
    """
    
    def __init__(self):
        self.retriever = DocumentRetriever()
        
        # Load retrieval config
        self.retrieval_config = config_loader.get("rag_retrieval", {})        
        logger.info("RAGPipeline initialized - pure retrieval, no hardcoded parsing")
    
    def query(
        self,
        query: str,
        city: Optional[str] = None,
        state: Optional[str] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Query the RAG system.
        city and state are ONLY used for prompt context, NOT for filtering.
        """
        chunks = self.retriever.retrieve(
                query=query,
                state=state,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        
        if not chunks:
            return {
                'answer': "",
                'raw_chunks': [],
                'has_results': False,
            }
        
        return {
            'raw_chunks': [
                {
                    'text': chunk.text,
                    'source': chunk.source,
                    'section': chunk.section,
                    'topic': chunk.topic,
                    'score': chunk.score,
                    'jurisdiction': chunk.jurisdiction,
                }
                for chunk in chunks
            ],
            'has_results': True,
        }
    
    def get_compliance_requirements(self, concept: str, city: str, state: str) -> Dict[str, Any]:
        """
        Get compliance requirements - uses rag_retrieval config.
        Simple, config-driven approach.
        """
        # Simple queries that work - these could also be moved to config if needed
        queries = [
            f"{concept} licensing requirements",
            f"{concept} permits and registrations",
            f"{concept} FSSAI requirements",
        ]
        
        all_raw_chunks = []
        seen_keys = set()
        
        for query in queries:
            logger.info(f"Compliance query: {query}")
            result = self.query(query=query, city=city, state=state)
            
            for chunk in result.get('raw_chunks', []):
                unique_key = f"{chunk.get('source', '')}_{chunk.get('text', '')[:100]}"
                if unique_key not in seen_keys:
                    seen_keys.add(unique_key)
                    all_raw_chunks.append(chunk)
        
        all_raw_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.info(f"Compliance retrieval: found {len(all_raw_chunks)} unique chunks")
        
        return {
            'raw_chunks': all_raw_chunks,
            'city': city,
            'state': state,
            'concept': concept,
            'has_results': len(all_raw_chunks) > 0,
        }


def get_rag_pipeline() -> RAGPipeline:
    """Get singleton RAG pipeline instance."""
    return RAGPipeline()


if __name__ == "__main__":
    rag = get_rag_pipeline()
    
    result = rag.get_compliance_requirements(
        concept="Restaurant",
        city="Pune",
        state="Maharashtra"
    )
    
    print(f"\n=== Results ===")
    print(f"Has results: {result['has_results']}")
    print(f"Raw chunks returned: {len(result['raw_chunks'])}")
    
    if result['raw_chunks']:
        print(f"\nFirst chunk:")
        print(f"  Source: {result['raw_chunks'][0]['source']}")
        print(f"  Score: {result['raw_chunks'][0]['score']:.3f}")
        print(f"  Preview: {result['raw_chunks'][0]['text'][:150]}...")