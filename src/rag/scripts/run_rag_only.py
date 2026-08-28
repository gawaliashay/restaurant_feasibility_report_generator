# run_rag_only.py
"""
Manual RAG smoke test — run: python -m src.rag.scripts.run_rag_only
"""

from src.rag.retriever.retriever import get_retriever

retriever = get_retriever()

queries = [
    "FSSAI Act penalties",
    "Maharashtra Shops and Establishment Act",
    "restaurant licenses and permits",
]

for q in queries:
    print(f"\n{'='*60}")
    print(f"Query: {q}")
    print("=" * 60)

    results = retriever.retrieve(q, top_k=5)

    print(f"Retrieved: {len(results)} chunks")
    for r in results:
        source = r.metadata.get("document_name", "Unknown")
        print(f"  Source: {source}")
        print(f"  Score: {r.score:.3f}")
        print(f"  Text: {r.text[:100]}...")
        print()
