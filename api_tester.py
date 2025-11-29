
# Test script
from src.configuration.config_loader import config_loader

config = config_loader.get()
print("Tavily API Key loaded:", bool(config['apis']['tavily']['api_key']))
print("SerpAPI API Key loaded:", bool(config['apis']['serpapi']['api_key']))
print("GROQ API Key loaded:", bool(config['models']['llms']['groq']['api_key']))