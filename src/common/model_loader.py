# src/model_loader/model_loader.py

import importlib
from typing import Any, Dict
from src.configuration.config_loader import config_loader
from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException

class ModelLoader:
    def __init__(self):
        self.defaults = config_loader.get("defaults")
        self.llm_configs = config_loader.get("models.llms")

    def _load_class(self, import_path: str):
        try:
            module_path, class_name = import_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            raise CustomException(f"Failed dynamic import: {import_path}", e)

    def get_provider_name(self, purpose: str) -> str:
        # purpose options: primary_llm, fast_llm, creative_llm, analysis_llm
        if purpose not in self.defaults:
            raise CustomException(f"Invalid LLM purpose: {purpose}", None)
        return self.defaults[purpose]

    def get_config(self, provider: str) -> Dict[str, Any]:
        cfg = self.llm_configs.get(provider)
        if not cfg:
            raise CustomException(f"Unknown LLM provider: {provider}", None)
        return cfg

    def load_llm(self, provider: str) -> Any:
        cfg = self.get_config(provider)

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
        provider = self.get_provider_name(purpose)
        return self.load_llm(provider)


model_loader = ModelLoader()
