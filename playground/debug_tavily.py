# playground/debug_tavily.py - Updated

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.common.tool_loader import use_tavily_search, _get_tavily_client
from src.configuration.config_loader import config_loader

print("=" * 60)
print("TAVILY DEBUG - TESTING DIFFERENT QUERIES")
print("=" * 60)

test_queries = [
    ["momo restaurant Pune"],  # Simpler
    ["restaurant market Pune"],  # Broader
    ["food delivery Pune"],  # Different angle
    ["Pune restaurant business"],  # General
    ["momo restaurant in India"],  # Country level
]

for query in test_queries:
    print(f"\nTesting: {query}")
    state = {"search_query": query}
    result = use_tavily_search(state)
    count = result.get('sources_count', 0)
    status = result.get('status', 'unknown')
    print(f"  Status: {status}, Results: {count}")
    
    if count > 0:
        print(f"  First result: {result['data']['results'][0].get('title', 'N/A')[:80]}")