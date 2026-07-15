# playground/debug_tavily_raw.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_tavily import TavilySearch
from src.configuration.config_loader import config_loader

print("=" * 60)
print("TAVILY RAW CLIENT DEBUG")
print("=" * 60)

# 1. Get API key
api_key = config_loader.get("apis.tavily.api_key")
print(f"\n1. API Key: {'✅ Present' if api_key else '❌ Missing'}")
if api_key:
    print(f"   Length: {len(api_key)}")
    print(f"   First 4 chars: {api_key[:4]}...")
    print(f"   Last 4 chars: ...{api_key[-4:]}")

# 2. Try to initialize client directly
print(f"\n2. Initializing Tavily client...")
try:
    client = TavilySearch(
        max_results=5, 
        tavily_api_key=api_key
    )
    print(f"   ✅ Client initialized successfully")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# 3. Test a simple search
print(f"\n3. Testing simple search...")
try:
    result = client.invoke({"query": "restaurant"})
    results = result.get("results", [])
    print(f"   Results: {len(results)}")
    if results:
        print(f"   First result: {results[0].get('title', 'N/A')}")
    else:
        print(f"   ⚠️ No results returned")
except Exception as e:
    print(f"   ❌ Search failed: {e}")

# 4. Check Tavily version and status
print(f"\n4. Checking Tavily client attributes...")
print(f"   Client type: {type(client)}")
print(f"   Client methods: {[m for m in dir(client) if not m.startswith('_')]}")

# 5. Try with different parameters
print(f"\n5. Trying search_depth='advanced'...")
try:
    result = client.invoke({
        "query": "restaurant",
        "search_depth": "advanced"
    })
    results = result.get("results", [])
    print(f"   Results: {len(results)}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# 6. Check if there's an error message in the response
print(f"\n6. Checking response structure...")
try:
    result = client.invoke({"query": "test"})
    print(f"   Response keys: {list(result.keys())}")
    if "error" in result:
        print(f"   Error: {result['error']}")
    if "message" in result:
        print(f"   Message: {result['message']}")
except Exception as e:
    print(f"   ❌ Failed: {e}")

print("\n" + "=" * 60)
print("DEBUG COMPLETE")
print("=" * 60)