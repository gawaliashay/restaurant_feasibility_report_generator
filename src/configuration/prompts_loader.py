# src/configuration/prompts_loader.py

"""Load prompts.yaml; return template strings by section and name."""

import yaml
from pathlib import Path
from typing import Any

from src.logging_exception.exception.custom_exception import CustomException
from src.logging_exception.logging.logger import logger


class PromptsLoader:
    def __init__(self, path: str = "src/configuration/prompts.yaml"):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Prompts file not found: {self.path}")
        try:
            with open(self.path, encoding="utf-8") as f:
                self.prompts: dict[str, Any] = yaml.safe_load(f) or {}
            logger.info("Prompts loaded", path=str(self.path))
        except Exception as exc:
            raise CustomException(f"Failed to load prompts from {self.path}", exc)

    def get_prompt(self, section: str, name: str, default: str | None = None) -> str:
        text = self.prompts.get(section, {}).get(name)
        if text is None:
            if default is not None:
                logger.warning("Prompt not found, using default", section=section, name=name)
                return default
            raise KeyError(f"Prompt not found: {section}.{name}")
        return text


prompts_loader = PromptsLoader()
