# test_rag_queries.py
"""
Test RAG retrieval with different queries.
"""

from src.rag.rag_pipeline import get_rag_pipeline

rag = get_rag_pipeline()

queries = [
    "FSSAI Act penalties",
    "Maharashtra Shops and Establishment Act",
    "working hours Maharashtra restaurant",
    "restaurant licenses and permits",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    print('='*60)
    
    results = rag.retrieve(q, top_k=5)
    
    print(f"Retrieved: {len(results)} chunks\n")
    
    for i, chunk in enumerate(results):
        print(f"[{i+1}] Score: {chunk.score:.4f}")
        print(f"    Source: {chunk.metadata.get('document_name', 'Unknown')}")
        print(f"    Text: {chunk.text[:300]}...")
        print("-" * 40)