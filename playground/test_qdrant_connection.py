# test_qdrant_connection.py

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

url = os.getenv('QDRANT_URL')
api_key = os.getenv('QDRANT_API_KEY')

# Check if values exist
if not url:
    print("❌ QDRANT_URL is not set in .env file")
    exit(1)

if not api_key:
    print("❌ QDRANT_API_KEY is not set in .env file")
    exit(1)

print(f"URL: {url}")
print(f"API Key: {api_key[:20]}...")

try:
    # Attempt 1: Standard connection with integer timeout
    print("\nAttempt 1: Standard connection...")
    client = QdrantClient(
        url=url,
        api_key=api_key,
        timeout=30  # Use int, not float
    )
    
    # Test get collections
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]
    print(f"✅ Connected! Collections: {collection_names}")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    
    # Attempt 2: Remove port if present (for cloud)
    if '.cloud.qdrant.io' in url:
        # Remove port if present
        if ':6333' in url or ':6334' in url:
            try_url = url.split(':')[0] + ':' + url.split(':')[1]  # Keep https://
            print(f"\nAttempt 2: Removing port from URL...")
            print(f"New URL: {try_url}")
            try:
                client = QdrantClient(
                    url=try_url,
                    api_key=api_key,
                    timeout=30,
                    prefer_grpc=False
                )
                collections = client.get_collections()
                collection_names = [c.name for c in collections.collections]
                print(f"✅ Connected! Collections: {collection_names}")
            except Exception as e2:
                print(f"❌ Still failed: {e2}")
    else:
        # Attempt 3: Try without https:// for local
        if url.startswith('https://'):
            try_url = url.replace('https://', '')
            print(f"\nAttempt 3: Trying without https://...")
            print(f"New URL: {try_url}")
            try:
                client = QdrantClient(
                    url=try_url,
                    api_key=api_key,
                    timeout=30,
                    prefer_grpc=False
                )
                collections = client.get_collections()
                collection_names = [c.name for c in collections.collections]
                print(f"✅ Connected! Collections: {collection_names}")
            except Exception as e3:
                print(f"❌ Still failed: {e3}")