# src/common/model_loader.py

"""Load chat LLMs and embedding models from configs.yaml."""

import importlib
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from src.configuration.config_loader import config_loader
from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger

import importlib
from typing import Any, Dict
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException

class ModelLoader:
    def __init__(self):
        self.defaults = config_loader.get("defaults") or {}
        self.llm_configs = config_loader.get("models.llms") or {}
        self.embedding_configs = config_loader.get("rag_embeddings") or {}

    def _load_class(self, import_path: str):
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            return getattr(importlib.import_module(module_path), class_name)
        except Exception as error:
            raise CustomException(f"Failed dynamic import: {import_path}", error)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=2, max=8))
    def get_llm(self, purpose: str) -> Any:
        provider = self.defaults.get(purpose)
        if not provider:
            raise CustomException(f"Invalid LLM purpose: {purpose}", None)

        config = self.llm_configs.get(provider)
        if not config:
            raise CustomException(f"Unknown LLM provider: {provider}", None)

        import_path = config.get("import_path")
        if not import_path:
            raise CustomException(f"No import_path configured for LLM: {provider}", None)

        model_name = config.get("model") or config.get("model_name")
        api_key = config.get("api_key")
        if not api_key:
            raise CustomException(f"No API key configured for LLM: {provider}", None)

        params = {
            "model": model_name,
            "api_key": api_key,
            "temperature": config.get("temperature", 0.3),
            "max_tokens": config.get("max_tokens", 2048),
        }

        try:
            instance = self._load_class(import_path)(**params)
            logger.info(
                "Loaded LLM",
                provider=provider,
                model=model_name,
                max_tokens=params["max_tokens"],
            )
            return instance
        except Exception as error:
            raise CustomException(f"Failed to initialize LLM for {provider}", error)

    def get_embeddings(self, purpose: str | None = None) -> Any:
        if purpose and purpose in self.embedding_configs:
            provider = purpose
        else:
            provider = self.embedding_configs.get("default", "openai")

        config = self.embedding_configs.get(provider)
        if not config:
            raise CustomException(f"Unknown embedding provider: {provider}", None)

        import_path = config.get("import_path")
        if not import_path:
            raise CustomException(f"No import_path configured for embedding: {provider}", None)

        model_name = config.get("model_name")
        params: dict[str, Any] = {}
        if model_name:
            params["model"] = model_name

        api_key = config.get("api_key")
        if api_key:
            params["google_api_key" if provider == "google" else "api_key"] = api_key

        try:
            instance = self._load_class(import_path)(**params)
            logger.info("Loaded embedding model", model=model_name, provider=provider)
            return instance
        except Exception as error:
            raise CustomException(f"Failed to initialize embedding for {provider}", error)


model_loader = ModelLoader()
