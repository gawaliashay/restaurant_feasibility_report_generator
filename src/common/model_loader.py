# src\common\model_loader.py

"""
Central model loader for LLMs and Embeddings.

Responsibilities:
- Dynamic import of model classes
- LLM loading (Groq, OpenAI, etc.)
- Embedding loading (OpenAI, HuggingFace, Google, etc.)
- Config-driven model initialization
- Retry logic for reliability
"""

import importlib
from typing import Any, Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException


# ================================================================
# BASE LOADER (Shared Logic)
# ================================================================

class ModelLoader:
    """
    Central loader for:
        - Chat LLMs
        - Embedding models

    Configuration comes from configs.yaml.
    """

    def __init__(self):
        self.defaults = config_loader.get("defaults") or {}
        self.llm_configs = config_loader.get("models.llms") or {}
        self.embedding_configs = config_loader.get("rag_embeddings") or {}

    # ----------------------------------------------------------------
    # Dynamic Import
    # ----------------------------------------------------------------

    def _load_class(self, import_path: str):
        """
        Dynamically import a class from a dotted path.

        Example:
            langchain_groq.ChatGroq
        """
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)

        except Exception as error:
            raise CustomException(
                f"Failed dynamic import: {import_path}",
                error,
            )


# ================================================================
# LLM LOADER
# ================================================================

    # ----------------------------------------------------------------
    # Provider Resolution
    # ----------------------------------------------------------------

    def get_llm_provider_name(self, purpose: str) -> str:
        """
        Resolve purpose -> provider.

        Example:
            creative_llm -> groq
        """
        provider = self.defaults.get(purpose)

        if not provider:
            raise CustomException(
                f"Invalid LLM purpose: {purpose}",
                None,
            )

        return provider

    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for an LLM provider.
        """
        config = self.llm_configs.get(provider)

        if not config:
            raise CustomException(
                f"Unknown LLM provider: {provider}",
                None,
            )

        return config

    # ----------------------------------------------------------------
    # Load LLM
    # ----------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=8),
    )
    def load_llm(self, provider: str) -> Any:
        """
        Create an LLM instance.

        NOTE:
            max_tokens is loaded from configs.yaml.
            The report compiler can still override max_tokens
            per request when supported by LangChain.
        """
        config = self.get_llm_config(provider)

        import_path = config.get("import_path")

        if not import_path:
            raise CustomException(
                f"No import_path configured for LLM: {provider}",
                None,
            )

        llm_class = self._load_class(import_path)

        # Model name
        model_name = config.get("model") or config.get("model_name")

        # API key
        api_key = config.get("api_key")

        if not api_key:
            raise CustomException(
                f"No API key configured for LLM: {provider}",
                None,
            )

        # Model parameters
        params = {
            "model": model_name,
            "api_key": api_key,
            "temperature": config.get("temperature", 0.3),
            "max_tokens": config.get("max_tokens", 2048),
        }

        try:
            instance = llm_class(**params)

            logger.info(
                "Loaded LLM: %s | model=%s | max_tokens=%s",
                provider,
                model_name,
                params["max_tokens"],
            )

            return instance

        except Exception as error:
            raise CustomException(
                f"Failed to initialize LLM for {provider}",
                error,
            )

    def get_llm(self, purpose: str) -> Any:
        """
        Get LLM using a configured purpose.

        Example:
            get_llm("creative_llm")
        """
        provider = self.get_llm_provider_name(purpose)
        return self.load_llm(provider)


# ================================================================
# EMBEDDING LOADER
# ================================================================

    # ----------------------------------------------------------------
    # Provider Resolution
    # ----------------------------------------------------------------

    def get_embedding_provider_name(self, purpose: Optional[str] = None) -> str:
        """
        Resolve embedding provider.
        """
        if purpose and purpose in self.embedding_configs:
            return purpose

        return self.embedding_configs.get("default", "openai")

    def get_embedding_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Get embedding configuration.
        """
        if provider is None:
            provider = self.get_embedding_provider_name()

        config = self.embedding_configs.get(provider)

        if not config:
            raise CustomException(
                f"Unknown embedding provider: {provider}",
                None,
            )

        return config

    # ----------------------------------------------------------------
    # Load Embeddings
    # ----------------------------------------------------------------

    def load_embeddings(self, provider: Optional[str] = None) -> Any:
        """
        Create embedding model.
        """
        if provider is None:
            provider = self.get_embedding_provider_name()

        config = self.get_embedding_config(provider)

        import_path = config.get("import_path")

        if not import_path:
            raise CustomException(
                f"No import_path configured for embedding: {provider}",
                None,
            )

        embedding_class = self._load_class(import_path)

        model_name = config.get("model_name")

        params: Dict[str, Any] = {}

        if model_name:
            params["model"] = model_name

        api_key = config.get("api_key")

        if api_key:
            if provider == "google":
                params["google_api_key"] = api_key
            else:
                params["api_key"] = api_key

        try:
            instance = embedding_class(**params)

            logger.info(
                "Loaded Embedding model: %s (%s)",
                model_name,
                provider,
            )

            return instance

        except Exception as error:
            raise CustomException(
                f"Failed to initialize Embedding for {provider}",
                error,
            )

    def get_embeddings(self, purpose: Optional[str] = None) -> Any:
        """
        Get embeddings using configured provider.
        """
        provider = self.get_embedding_provider_name(purpose)
        return self.load_embeddings(provider)


# ================================================================
# SINGLETON
# ================================================================

model_loader = ModelLoader()