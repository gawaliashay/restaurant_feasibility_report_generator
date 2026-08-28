# run_rag_queries.py
"""
Manual RAG query smoke test — run: python -m src.rag.scripts.run_rag_queries
"""

from src.rag.retriever.retriever import get_retriever

retriever = get_retriever()

queries = [
    "FSSAI Act penalties",
    "Maharashtra Shops and Establishment Act",
    "working hours Maharashtra restaurant",
    "restaurant licenses and permits",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    print("=" * 60)

    results = retriever.retrieve(q, top_k=5)

    print(f"Retrieved: {len(results)} chunks\n")

    for i, chunk in enumerate(results):
        print(f"[{i+1}] Score: {chunk.score:.4f}")
        print(f"    Source: {chunk.metadata.get('document_name', 'Unknown')}")
        print(f"    Text: {chunk.text[:300]}...")
        print("-" * 40)
