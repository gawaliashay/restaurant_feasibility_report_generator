# main.py

import sys
import os

from src.workflow.research_orchestrator import main as research_main


# def quick_test():
#     from src.common.tool_loader import (
#         use_tavily_search,
#         use_google_trends,
#         use_openstreetmap,
#         use_google_maps,
#         check_serpapi_key,
#     )

#     print("Running quick tool tests")

#     # Tavily
#     print("\n[Test] Tavily Search")
#     try:
#         r = use_tavily_search({"search_query": "momo market India"})
#         print("Status:", "ok" if "results" in r else "fail")
#         print("Items:", len(r.get("results", [])))
#     except Exception as e:
#         print("Error:", str(e))

#     # Google Trends
#     print("\n[Test] Google Trends")
#     try:
#         r = use_google_trends({"trend_query": "momo Pune"})
#         print("Status:", "ok" if "data" in r else "fail")
#         print("Points:", len(r.get("data", {})))
#     except Exception as e:
#         print("Error:", str(e))

#     # OpenStreetMap
#     print("\n[Test] OpenStreetMap")
#     try:
#         r = use_openstreetmap({"location": "Warje, Pune, Maharashtra, India"})
#         print("Status:", "ok" if "latitude" in r else "fail")
#         print("Lat:", r.get("latitude"))
#         print("Lon:", r.get("longitude"))
#     except Exception as e:
#         print("Error:", str(e))

#     # Google Maps
#     print("\n[Test] Google Maps")
#     try:
#         if not check_serpapi_key():
#             print("SerpAPI key missing")
#         else:
#             r = use_google_maps({"location": "Warje, Pune, Maharashtra, India"})
#             print("Status:", "ok" if "results" in r else "fail")
#             print("Results:", r.get("results_count", 0))
#     except Exception as e:
#         print("Error:", str(e))

#     print("\nQuick tests completed")


if __name__ == "__main__":
    # quick_test()
    research_main()
