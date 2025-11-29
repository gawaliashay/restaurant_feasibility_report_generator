import importlib
from src.configuration.config_loader import config_loader


class ModelLoader:
    """Minimal LLM loader for Restaurant Research System."""

    def load_llm(self, provider: str = "groq") -> any:
        """Load LLM by provider name."""
        llm_cfg = config_loader.get_llm_config(provider)
        if not llm_cfg:
            raise Exception(f"LLM config not found: {provider}")
        
        module_path, class_name = llm_cfg["import_path"].rsplit(".", 1)
        cls = getattr(importlib.import_module(module_path), class_name)
        
        # Remove import_path from config
        kwargs = {k: v for k, v in llm_cfg.items() if k != "import_path"}
        
        # Handle parameter mapping for different providers
        kwargs = self._normalize_parameters(kwargs, provider)
        
        return cls(**kwargs)

    def _normalize_parameters(self, kwargs: dict, provider: str) -> dict:
        """Normalize parameter names across different LLM providers."""
        normalized = kwargs.copy()
        
        # Handle model parameter mapping
        if "model_name" in normalized and "model" not in normalized:
            normalized["model"] = normalized.pop("model_name")
        
        # Groq specific: Make sure model is set
        if provider == "groq" and "model" not in normalized:
            # Use the model from llm config section
            llm_config = config_loader.get('llm', {})
            if provider == "groq":
                if "main_model" in llm_config:
                    normalized["model"] = llm_config["main_model"]
                elif "fast_model" in llm_config:
                    normalized["model"] = llm_config["fast_model"]
        
        return normalized


# Singleton
model_loader = ModelLoader()