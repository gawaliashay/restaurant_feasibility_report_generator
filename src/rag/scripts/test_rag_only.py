# test_rag_only.py
"""
Test RAG retrieval without running the full pipeline.
"""

from src.rag.rag_pipeline import get_rag_pipeline

rag = get_rag_pipeline()

queries = [
    "FSSAI Act penalties",
    "Maharashtra Shops and Establishment Act",
    "restaurant licenses and permits",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    print('='*60)
    
    results = rag.retrieve(q, top_k=5)
    
    print(f"Retrieved: {len(results)} chunks")
    for r in results:
        source = r.metadata.get('document_name', 'Unknown')
        print(f"  Source: {source}")
        print(f"  Score: {r.score:.3f}")
        print(f"  Text: {r.text[:100]}...")
        print()