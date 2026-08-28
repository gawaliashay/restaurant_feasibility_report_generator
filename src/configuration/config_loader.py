# src/configuration/config_loader.py

"""Load .env + YAML config; resolve ${ENV_VAR}; dot-notation get()."""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.logging_exception.logging.logger import logger


class ConfigLoader:
    def __init__(
        self,
        env_path: str = ".env",
        config_path: str = "src/configuration/configs.yaml",
    ):
        self.env_path = Path(env_path)
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}

        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info("Loaded environment", env_path=str(self.env_path))

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with self.config_path.open("r", encoding="utf-8") as f:
            self._config = self._resolve_env_vars(yaml.safe_load(f) or {})

        logger.info("Configuration loaded")

    def _resolve_env_vars(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._resolve_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._resolve_env_vars(v) for v in data]
        if isinstance(data, str):
            matches = re.findall(r"\$\{([^}]+)\}", data)
            result = data
            for name in matches:
                val = os.getenv(name)
                if val is not None:
                    result = result.replace(f"${{{name}}}", val)
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
        value: Any = self._config
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value


config_loader = ConfigLoader()
