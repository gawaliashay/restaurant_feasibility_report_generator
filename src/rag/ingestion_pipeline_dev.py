# src\rag\ingestion_pipeline_dev.py
"""
Ingestion Pipeline for RAG Vector Store - Main Pipeline
Uses RecursiveCharacterTextSplitter for reliable chunking

Usage:
    python -m src.rag.ingestion_pipeline_dev
    python -m src.rag.ingestion_pipeline_dev --recreate
    python -m src.rag.ingestion_pipeline_dev --dry-run
    python -m src.rag.ingestion_pipeline_dev --debug
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logging_exception.logging.logger import logger
from src.rag.parser import UniversalDocumentParser
from src.rag.vector_store import get_vector_store
from src.configuration.config_loader import config_loader

from langchain_text_splitters import RecursiveCharacterTextSplitter


class IngestionPipeline:
    """
    Main ingestion pipeline using RecursiveCharacterTextSplitter.
    Reliable, config-driven, with optional debug output.
    """
    
    def __init__(self, recreate_collection: bool = False, save_debug: bool = False):
        self.save_debug = save_debug
        self.ingestion_time = datetime.now()
        
        # Load config
        self.config = config_loader.get_all()
        
        # Get splitting config
        splitting = self.config.get("rag_splitting", {})
        strategy_name = splitting.get("default_strategy", "recursive_character")
        strategy = splitting.get(strategy_name, {})
        
        # Initialize parser
        self.parser = UniversalDocumentParser(
            enable_ocr=True,
            enable_table_structure=True,
            max_pages=100
        )
        
        # Create splitter from config
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=strategy.get("chunk_size", 512),
            chunk_overlap=strategy.get("chunk_overlap", 50),
            separators=strategy.get("separators", ["\n\n", "\n", ". ", " ", ""]),
            length_function=len,
        )
        
        # Vector store
        self.vector_store = get_vector_store(recreate=recreate_collection)
        
        # Document directory
        docs_path = self.config.get("rag_documents", {}).get("data_path", "data/raw")
        self.docs_dir = Path(docs_path)
        
        # Debug directories - only create if debug mode is on
        self.markdown_dir: Optional[Path] = None
        self.chunks_dir: Optional[Path] = None
        
        if save_debug:
            self.markdown_dir = Path("data/processed/markdown")
            self.chunks_dir = Path("data/processed/chunks")
            self.markdown_dir.mkdir(parents=True, exist_ok=True)
            self.chunks_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"IngestionPipeline initialized | chunk_size={strategy.get('chunk_size')}, docs={self.docs_dir}")
    
    def find_documents(self) -> List[Path]:
        """Find all PDF/DOCX/TXT/MD files."""
        docs = []
        for ext in ['.pdf', '.docx', '.txt', '.md']:
            docs.extend(self.docs_dir.rglob(f"*{ext}"))
        return list(set(docs))
    
    def save_markdown(self, content: str, file_path: Path) -> Optional[Path]:
        """Save parsed markdown (debug mode)."""
        if not self.save_debug or self.markdown_dir is None:
            return None
        
        md_path = self.markdown_dir / f"{file_path.stem}.md"
        md_path.write_text(content, encoding='utf-8')
        return md_path
    
    def save_chunks(self, chunks: List[Dict], file_path: Path) -> Optional[Path]:
        """Save chunks to JSON (debug mode)."""
        if not self.save_debug or self.chunks_dir is None:
            return None
        
        json_path = self.chunks_dir / f"{file_path.stem}_chunks.json"
        
        data = {
            'source': file_path.name,
            'processed_at': self.ingestion_time.isoformat(),
            'total_chunks': len(chunks),
            'chunks': [{'index': i, 'topic': c.get('topic'), 'text': c['text'][:500]} 
                       for i, c in enumerate(chunks)]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return json_path
    
    def process_document(self, file_path: Path) -> List[Dict]:
        """Parse -> chunk -> return chunks."""
        logger.info(f"Processing: {file_path.name}")
        
        # Parse
        result = self.parser.parse(file_path)
        content = result['content']
        
        if not content or len(content.strip()) < 100:
            logger.warning(f"  Low content: {len(content)} chars")
            return []
        
        logger.info(f"  Parsed: {len(content)} chars")
        
        # Save markdown (debug)
        self.save_markdown(content, file_path)
        
        # Split into chunks
        texts = self.splitter.split_text(content)
        logger.info(f"  Split into {len(texts)} chunks")
        
        # Create chunk dicts
        chunks = []
        for i, text in enumerate(texts):
            chunks.append({
                'text': text,
                'chunk_index': i,
                'topic': self._detect_topic(text),
                'metadata': {
                    'document_name': file_path.name,
                    'jurisdiction': self._detect_jurisdiction(file_path.name, content),
                    'chunk_size': len(text),
                }
            })
        
        # Save chunks (debug)
        self.save_chunks(chunks, file_path)
        
        return chunks
    
    def _detect_jurisdiction(self, filename: str, content: str) -> str:
        """Detect state from content."""
        states = self.config.get("rag_documents", {}).get("supported_states", [])
        for state in states:
            if state.lower() in filename.lower() or state.lower() in content.lower():
                return state
        return 'Central'
    
    def _detect_topic(self, text: str) -> str:
        """Simple topic detection."""
        text_lower = text.lower()
        topics = {
            'FSSAI': ['fssai', 'food safety'],
            'Licensing': ['license', 'permit', 'registration'],
            'Fire Safety': ['fire', 'noc'],
            'Labour': ['labour', 'shop', 'establishment'],
            'Tax': ['gst', 'tax'],
        }
        for topic, keywords in topics.items():
            if any(k in text_lower for k in keywords):
                return topic
        return 'General'
    
    def run(self, dry_run: bool = False) -> Dict:
        """Run the ingestion pipeline."""
        documents = self.find_documents()
        
        if not documents:
            raise ValueError(f"No documents found in {self.docs_dir}")
        
        all_chunks = []
        for doc in documents:
            chunks = self.process_document(doc)
            if chunks:
                all_chunks.extend(chunks)
                logger.info(f"✓ {doc.name}: {len(chunks)} chunks")
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Total Documents: {len(documents)}")
        logger.info(f"Total Chunks: {len(all_chunks)}")
        logger.info(f"{'='*50}")
        
        # Store in vector DB
        if not dry_run and all_chunks:
            logger.info("Storing chunks in Qdrant...")
            
            vector_chunks = [{
                'text': c['text'],
                'metadata': c['metadata'],
                'topic': c['topic'],
            } for c in all_chunks]
            
            self.vector_store.add_chunks(vector_chunks)
            
            info = self.vector_store.get_collection_info()
            logger.info(f"✓ Stored {info.get('points_count', 0)} points")
        
        return {'total_documents': len(documents), 'total_chunks': len(all_chunks)}


def main():
    parser = argparse.ArgumentParser(description="RAG Ingestion Pipeline")
    parser.add_argument("--recreate", action="store_true", help="Recreate collection")
    parser.add_argument("--dry-run", action="store_true", help="Process only, no storage")
    parser.add_argument("--debug", action="store_true", help="Save debug files")
    
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("🚀 STARTING INGESTION PIPELINE")
    logger.info("=" * 50)
    
    pipeline = IngestionPipeline(
        recreate_collection=args.recreate,
        save_debug=args.debug
    )
    
    try:
        summary = pipeline.run(dry_run=args.dry_run)
        logger.info(f"\n✅ Ingestion complete: {summary['total_chunks']} chunks from {summary['total_documents']} documents")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()