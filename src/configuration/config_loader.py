# src\configuration\config_loader.py

"""
Simple configuration loader.

Responsibilities:
- Load environment variables from .env.
- Load YAML configuration.
- Resolve ${ENV_VAR} placeholders.
- Provide universal .get() access with dot notation.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.logging_exception.logging.logger import logger


class ConfigLoader:
    """Universal YAML configuration loader with environment support."""

    def __init__(
        self,
        env_path: str = ".env",
        config_path: str = "src/configuration/configs.yaml",
    ):
        self.env_path = Path(env_path)
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}

        self._load_environment()
        self._config = self._load_config()

        logger.info("Configuration loaded successfully")

    def _load_environment(self) -> None:
        """Load environment variables from .env if available."""
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info("Loaded environment from %s", self.env_path)

    def _load_config(self) -> dict[str, Any]:
        """Load YAML configuration and resolve environment variables."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as config_file:
            raw_config = yaml.safe_load(config_file) or {}

        return self._resolve_env_vars(raw_config)

    def _resolve_env_vars(self, data: Any) -> Any:
        """Resolve ${ENV_VAR} placeholders recursively."""
        if isinstance(data, dict):
            return {
                key: self._resolve_env_vars(value)
                for key, value in data.items()
            }

        if isinstance(data, list):
            return [
                self._resolve_env_vars(value)
                for value in data
            ]

        if isinstance(data, str):
            pattern = r"\$\{([^}]+)\}"
            matches = re.findall(pattern, data)
            result = data

            for variable_name in matches:
                environment_value = os.getenv(variable_name)
                if environment_value is not None:
                    result = result.replace(
                        f"${{{variable_name}}}",
                        environment_value,
                    )

            if matches:
                if result.isdigit():
                    return int(result)
                if result.lower() == "true":
                    return True
                if result.lower() == "false":
                    return False

            return result

        return data

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Examples:
            config_loader.get("resource_limits.mode")
            config_loader.get("models.llms.openai.max_tokens", 1024)
            config_loader.get("research.sections.market_analysis.enabled")
        """
        keys = key.split(".")
        value: Any = self._config

        for part in keys:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value


# ============================================================================
# Singleton
# ============================================================================

config_loader = ConfigLoader()