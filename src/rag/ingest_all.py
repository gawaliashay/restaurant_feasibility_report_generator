"""
RAG Data Ingestion - Main entry point.
Loads all sources from configs.yaml into the vector store.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.configuration.config_loader import config_loader
from src.rag.ingestion.ingestion_pipeline import IngestionPipeline
from src.rag.vector_store.vector_store import get_vector_store


def ingest_all():
    """
    Main ingestion function.
    Called by the pipeline or run as a script.
    """
    # Check current data
    store = get_vector_store()
    info = store.get_collection_info()
    print(f"Current documents: {info['points']}")
    
    # Ask if want to clear
    if info['points'] > 0:
        choice = input(f"Found {info['points']} documents. Clear and re-ingest? (y/n): ")
        if choice.lower() == 'y':
            get_vector_store(recreate=True)
            print("Cleared!")
    
    # Get sources from config
    rag_sources = config_loader.get("rag_sources", {})
    if not rag_sources:
        print("⚠️  No rag_sources found in config")
        return
    
    pipeline = IngestionPipeline()
    total_chunks = 0
    
    # 1. Ingest local PDFs
    for source in rag_sources.get("local_pdfs", []) or []:
        path = Path(source.get("path", ""))
        if path.exists():
            result = pipeline.ingest_files([path])
            print(f"📄 {path.name}: {result['total_chunks']} chunks")
            total_chunks += result['total_chunks']
        else:
            print(f"⚠️  File not found: {path}")
    
    # 2. Ingest websites
    for source in rag_sources.get("websites", []) or []:
        url = source.get("url", "")
        result = pipeline.ingest_website(url)
        print(f"🌐 {source.get('title', url)}: {result.get('chunks', 0)} chunks")
        total_chunks += result.get('chunks', 0)
    
    # 3. Ingest online PDFs
    for source in rag_sources.get("online_pdfs", []) or []:
        url = source.get("url", "")
        result = pipeline.ingest_online_pdf(url)
        print(f"📎 {source.get('title', url)}: {result.get('chunks', 0)} chunks")
        total_chunks += result.get('chunks', 0)
    
    print(f"\n✅ Total chunks ingested: {total_chunks}")
    return total_chunks


if __name__ == "__main__":
    ingest_all()