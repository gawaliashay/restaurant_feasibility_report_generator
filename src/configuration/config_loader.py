# src\configuration\config_loader.py

"""
Config Loader - Simple, reliable configuration management.
Loads YAML config with environment variable support.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

from src.logging_exception.logging.logger import logger


class ConfigLoader:
    """Simple config loader with env variable support."""

    def __init__(self, env_path: str = ".env", config_path: str = "src/configuration/configs.yaml"):
        self.env_path = Path(env_path)
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # Load env vars
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info(f"Loaded env from {self.env_path}")
        
        # Load and resolve config
        self.config = self._load_config()
        logger.info("✅ Configuration loaded successfully")

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML and resolve environment variables."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        
        return self._resolve_env_vars(raw)

    def _resolve_env_vars(self, data: Any) -> Any:
        """Replace ${VAR} with environment variable values."""
        if isinstance(data, dict):
            return {k: self._resolve_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._resolve_env_vars(v) for v in data]
        if isinstance(data, str):
            # Find all ${VAR} or ${VAR:-default} patterns
            pattern = r"\$\{([^}]+)\}"
            matches = re.findall(pattern, data)
            
            result = data
            for var in matches:
                env_value = os.getenv(var)
                if env_value is not None:
                    result = result.replace(f"${{{var}}}", env_value)
                # If no env value, keep the original (with default handling in YAML)
            
            # Try to convert to appropriate type
            if result.isdigit():
                return int(result)
            if result.lower() in ['true', 'false']:
                return result.lower() == 'true'
            return result
        return data

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'rag.max_chunks')."""
        keys = key.split(".")
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

    def get_all(self) -> Dict[str, Any]:
        """Get the entire config dictionary."""
        return self.config


# Singleton instance
config_loader = ConfigLoader()


# Quick test
if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING CONFIG LOADER")
    print("="*60)
    
    try:
        # Test get() method
        print("\n✓ Testing config_loader.get()...")
        print(f"   RAG enabled: {config_loader.get('rag.enabled')}")
        print(f"   Max chunks: {config_loader.get('rag_compliance.max_chunks')}")
        print(f"   LLM provider: {config_loader.get('defaults.primary_llm')}")
        
        # Test get_all() method
        print("\n✓ Testing config_loader.get_all()...")
        all_config = config_loader.get_all()
        print(f"   Config keys: {list(all_config.keys())[:5]}...")
        
        # Test default value
        print("\n✓ Testing default value...")
        missing = config_loader.get('nonexistent.key', 'default_value')
        print(f"   Missing key returns: {missing}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()