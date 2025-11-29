# src\configuration\prompts_loader.py

import yaml
from pathlib import Path
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException


class PromptsLoader:
    """Load and access YAML-based prompt configurations for Restaurant Research System."""

    def __init__(self, path: str = "src/configuration/prompts.yaml"):
        self.path = Path(path)
        self.prompts: Dict[str, Any] = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML into a dictionary."""
        if not self.path.exists():
            raise FileNotFoundError(f"Prompts file not found: {self.path}")

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            logger.info(f"Prompts loaded successfully from: {self.path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load prompts from {self.path}: {e}")
            raise CustomException(f"Failed to load prompts from {self.path}", e)

    def get_prompt(self, section: str, name: str, default: str = None) -> str:
        """Return prompt template string for given section and name."""
        try:
            prompt_text = self.prompts.get(section, {}).get(name)
            if prompt_text is None:
                if default is not None:
                    logger.warning(f"Prompt not found: {section}.{name}, using default")
                    return default
                raise KeyError(f"Prompt not found: {section}.{name}")
            return prompt_text
        except Exception as e:
            logger.error(f"Error getting prompt {section}.{name}: {e}")
            if default is not None:
                return default
            raise

    def get_chat_prompt(self, section: str, name: str, default: str = None) -> ChatPromptTemplate:
        """Return a ChatPromptTemplate for given section and name."""
        prompt_text = self.get_prompt(section, name, default)
        return ChatPromptTemplate.from_template(prompt_text)

    def get_section(self, section: str) -> Dict[str, str]:
        """Return all prompts in a section."""
        return self.prompts.get(section, {})

    def get_all_prompts(self) -> Dict[str, Any]:
        """Return all loaded prompts."""
        return self.prompts

    def list_sections(self) -> list:
        """Return list of all available sections."""
        return list(self.prompts.keys())

    def list_prompts_in_section(self, section: str) -> list:
        """Return list of all prompt names in a section."""
        return list(self.prompts.get(section, {}).keys())


# Ready-to-use instance
prompts_loader = PromptsLoader()