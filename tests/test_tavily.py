from tavily import TavilyClient
import os

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

response = client.search(
    query="What are the best momo restaurants in Baner Pune?",
    max_results=5,
)

print(response)