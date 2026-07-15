# src\common\model_loader.py

import importlib
from typing import Any, Dict, Optional
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException
from tenacity import retry, stop_after_attempt, wait_exponential


class ModelLoader:
    def __init__(self):
        self.defaults = config_loader.get("defaults")
        self.llm_configs = config_loader.get("models.llms")
        self.embedding_configs = config_loader.get("rag_embeddings", {})

    def _load_class(self, import_path: str):
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            raise CustomException(f"Failed dynamic import: {import_path}", e)

    # =====================================
    # LLM Methods
    # =====================================
    def get_llm_provider_name(self, purpose: str) -> str:
        if purpose not in self.defaults:
            raise CustomException(f"Invalid LLM purpose: {purpose}", None)
        return self.defaults[purpose]

    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        cfg = self.llm_configs.get(provider)
        if not cfg:
            raise CustomException(f"Unknown LLM provider: {provider}", None)
        return cfg

    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def load_llm(self, provider: str) -> Any:
        cfg = self.get_llm_config(provider)
        import_path = cfg["import_path"]
        llm_class = self._load_class(import_path)

        try:
            instance = llm_class(
                model=cfg.get("model") or cfg.get("model_name"),
                api_key=cfg["api_key"],
                temperature=cfg["temperature"],
                max_tokens=cfg["max_tokens"]
            )
            logger.info(f"Loaded LLM: {provider}")
            return instance
        except Exception as e:
            raise CustomException(f"Failed to initialize LLM for {provider}", e)

    def get_llm(self, purpose: str) -> Any:
        provider = self.get_llm_provider_name(purpose)
        return self.load_llm(provider)

    # =====================================
    # Embedding Methods
    # =====================================
    def get_embedding_provider_name(self, purpose: Optional[str] = None) -> str:
        if purpose and purpose in self.embedding_configs:
            return purpose
        return self.embedding_configs.get("default", "openai")

    def get_embedding_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        if provider is None:
            provider = self.get_embedding_provider_name()
        
        cfg = self.embedding_configs.get(provider)
        if not cfg:
            raise CustomException(f"Unknown embedding provider: {provider}", None)
        return cfg

    def load_embeddings(self, provider: Optional[str] = None) -> Any:
        cfg = self.get_embedding_config(provider)
        import_path = cfg["import_path"]
        embedding_class = self._load_class(import_path)
        
        try:
            params = {"model": cfg.get("model_name")}
            if "api_key" in cfg and cfg["api_key"]:
                if provider == "google":
                    params["google_api_key"] = cfg["api_key"]
                else:
                    params["api_key"] = cfg["api_key"]
                        
            instance = embedding_class(**params)
            logger.info(f"Loaded Embedding model: {cfg.get('model_name')} ({provider})")
            return instance
        except Exception as e:
            raise CustomException(f"Failed to initialize Embedding for {provider}", e)

    def get_embeddings(self, purpose: Optional[str] = None) -> Any:
        provider = self.get_embedding_provider_name(purpose)
        return self.load_embeddings(provider)


model_loader = ModelLoader()