# check_store.py
from src.rag.vector_store.vector_store import get_vector_store

store = get_vector_store()

# Get collection info
info = store.get_collection_info()
print(f"Total chunks: {info['points']}")

# Search for FSSAI
results = store.search("FSSAI", top_k=5)
print(f"\nFound {len(results)} chunks with 'FSSAI':")
for r in results:
    print(f"  Source: {r['metadata'].get('document_name', 'Unknown')}")
    print(f"  Score: {r['score']:.3f}")

# Search for Maharashtra
results = store.search("Maharashtra", top_k=5)
print(f"\nFound {len(results)} chunks with 'Maharashtra':")
for r in results:
    print(f"  Source: {r['metadata'].get('document_name', 'Unknown')}")
    print(f"  Score: {r['score']:.3f}")