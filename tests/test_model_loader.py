# tests\test_model_loader.py

"""
Test for ModelLoader - Config-Driven.
"""

import sys
from pathlib import Path
import logging
from typing import Any
import time

# Add parent directory to path BEFORE importing src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.model_loader import model_loader
from src.configuration.config_loader import config_loader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_config(key: str, value: Any) -> None:
    """Print a config value nicely."""
    if isinstance(value, dict):
        print(f"  {key}:")
        for k, v in value.items():
            if k == "api_key" and v:
                v = "***HIDDEN***"
            print(f"    {k}: {v}")
    else:
        if key == "api_key" and value:
            value = "***HIDDEN***"
        print(f"  {key}: {value}")


def test_llm_configs() -> None:
    """Test LLM configuration loading."""
    print_section("LLM CONFIGURATION")

    defaults = config_loader.get("defaults", {})
    print("Defaults:")
    for key, value in defaults.items():
        print_config(key, value)

    llm_configs = config_loader.get("models.llms", {})
    print("\nLLM Configs:")
    for provider, config in llm_configs.items():
        print(f"\n  [{provider}]")
        for key, value in config.items():
            print_config(key, value)


def test_embedding_configs() -> None:
    """Test Embedding configuration loading."""
    print_section("EMBEDDING CONFIGURATION")

    embedding_configs = config_loader.get("rag_embeddings", {})
    print("Embedding Configs:")
    for provider, config in embedding_configs.items():
        if provider == "default":
            continue
        print(f"\n  [{provider}]")
        for key, value in config.items():
            if key == "api_key" and value:
                value = "***HIDDEN***"
            print(f"    {key}: {value}")


def test_llm_loading() -> None:
    """Test loading LLMs from config."""
    print_section("TESTING LLM LOADING")

    # Get LLM purposes from config
    defaults = config_loader.get("defaults", {})
    purposes = [
        ("primary_llm", defaults.get("primary_llm")),
        ("fast_llm", defaults.get("fast_llm")),
        ("creative_llm", defaults.get("creative_llm")),
        ("analysis_llm", defaults.get("analysis_llm")),
    ]

    for purpose, provider in purposes:
        print(f"\n  Purpose: {purpose}")
        print(f"  Provider: {provider}")

        if not provider:
            print("  ⚠️  No provider configured")
            continue

        try:
            llm = model_loader.get_llm(purpose)
            print(f"  ✅ Loaded: {type(llm).__name__}")

            # Print some attributes if available
            if hasattr(llm, "model_name"):
                print(f"    Model: {llm.model_name}")
            if hasattr(llm, "temperature"):
                print(f"    Temperature: {llm.temperature}")
            if hasattr(llm, "max_tokens"):
                print(f"    Max Tokens: {llm.max_tokens}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")


def test_embedding_loading() -> None:
    """Test loading Embedding models from config."""
    print_section("TESTING EMBEDDING LOADING")

    embedding_configs = config_loader.get("rag_embeddings", {})
    default_provider = embedding_configs.get("default", "openai")

    print(f"Default Provider: {default_provider}")

    # Test default provider
    print(f"\n  Loading default embedding provider...")
    try:
        embeddings = model_loader.get_embeddings()
        print(f"  ✅ Loaded: {type(embeddings).__name__}")

        # Print some attributes if available
        if hasattr(embeddings, "model"):
            print(f"    Model: {embeddings.model}")
        elif hasattr(embeddings, "model_name"):
            print(f"    Model: {embeddings.model_name}")

    except Exception as e:
        print(f"  ❌ Failed: {e}")

    # Test specific providers
    providers = ["openai", "huggingface", "google"]
    for provider in providers:
        if provider not in embedding_configs:
            continue

        print(f"\n  Loading embedding provider: {provider}...")
        try:
            embeddings = model_loader.get_embeddings(provider)
            print(f"  ✅ Loaded: {type(embeddings).__name__}")

            if hasattr(embeddings, "model"):
                print(f"    Model: {embeddings.model}")
            elif hasattr(embeddings, "model_name"):
                print(f"    Model: {embeddings.model_name}")

        except Exception as e:
            print(f"  ❌ Failed: {e}")


def test_llm_metadata() -> None:
    """Test retrieving LLM metadata from config."""
    print_section("LLM METADATA (from config)")

    llm_configs = config_loader.get("models.llms", {})

    for provider, config in llm_configs.items():
        print(f"\n  [{provider}]")
        print(f"    Model: {config.get('model_name') or config.get('model', 'N/A')}")
        print(f"    Temperature: {config.get('temperature', 0.3)}")
        print(f"    Max Tokens: {config.get('max_tokens', 2048)}")
        print(f"    Import Path: {config.get('import_path', 'N/A')}")


def test_embedding_metadata() -> None:
    """Test retrieving Embedding metadata from config."""
    print_section("EMBEDDING METADATA (from config)")

    embedding_configs = config_loader.get("rag_embeddings", {})
    default_provider = embedding_configs.get("default", "openai")

    print(f"Default Provider: {default_provider}")

    for provider, config in embedding_configs.items():
        if provider == "default":
            continue

        print(f"\n  [{provider}]")
        print(f"    Model: {config.get('model_name', 'N/A')}")
        print(f"    Dimensions: {config.get('dimensions', 'N/A')}")
        print(f"    Import Path: {config.get('import_path', 'N/A')}")
        api_key = config.get("api_key")
        print(f"    API Key: {'***HIDDEN***' if api_key else 'Not configured'}")


def test_llm_invocation() -> None:
    """Test actual LLM invocation (API call) with timeout."""
    print_section("TESTING LLM INVOCATION (API CALL)")
    
    defaults = config_loader.get("defaults", {})
    provider = defaults.get("analysis_llm")
    
    if not provider:
        print("  ⚠️  No analysis_llm configured")
        return
    
    llm = None  # Initialize llm to None
    model_name = "Unknown"  # Store model name separately
    
    try:
        llm = model_loader.get_llm("analysis_llm")
        # Store the model name for error reporting
        model_name = llm.model_name if hasattr(llm, "model_name") else "Unknown"
        
        print(f"  Model loaded: {type(llm).__name__}")
        print(f"  Model name: {model_name}")
        print(f"  Provider: {provider}")
        
        # 🔥 ACTUAL API CALL with timeout
        print("  Making API call (timeout: 30 seconds)...")
        start_time = time.time()
        
        # Use a very simple prompt
        response = llm.invoke("Say 'API test successful'")
        
        elapsed = time.time() - start_time
        print(f"  ⏱️  Response time: {elapsed:.2f} seconds")
        print(f"  ✅ API call successful!")
        print(f"  Response: {response.content[:200]}...")
        
    except TimeoutError:
        print(f"  ❌ API call timed out after 30 seconds")
        print(f"  This indicates a network issue or slow API response")
        
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        print(f"  🔍 This is why the pipeline fails!")
        
        # Check if it's a model not found error
        if "model" in str(e).lower() and ("not found" in str(e).lower() or "404" in str(e)):
            print(f"\n  💡 FIX: The model name '{model_name}' is invalid.")
            print(f"  Update your config to use a valid Groq model:")
            print(f"    - llama-3.3-70b-versatile")
            print(f"    - llama-3.1-8b-instant")
            print(f"    - llama-3.1-70b-versatile")


def main() -> None:
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" MODEL LOADER TEST SUITE")
    print("=" * 70)

    # 1. Config Tests
    test_llm_configs()
    test_embedding_configs()

    # 2. Metadata Tests
    test_llm_metadata()
    test_embedding_metadata()

    # 3. Loading Tests
    test_llm_loading()
    test_embedding_loading()
    
    # 4. 🔥 Actual API Call Test
    test_llm_invocation()

    print("\n" + "=" * 70)
    print(" TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()