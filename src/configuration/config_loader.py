# src/configuration/config_loader.py

import os
import yaml
import re
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from src.logging_exception.logging.logger import logger
from src.logging_exception.exception.custom_exception import CustomException


class PathsConfig(BaseModel):
    data: str
    vector_store: str
    reports: str

class AppConfig(BaseModel):
    name: str
    env: str
    host: str
    port: int
    cors_origins: str

class DefaultsConfig(BaseModel):
    primary_llm: str        
    team_creator_llm: str     
    research_llm: str
    report_compiler_llm: str

class ResearchConfig(BaseModel):
    max_analysts: int
    max_retries: int
    tavily_max_results: int

class APIConfig(BaseModel):
    tavily: Dict[str, str]
    serpapi: Dict[str, str]

class ExportConfig(BaseModel):
    formats: list
    timestamp_format: str

class AnalysisConfig(BaseModel):
    max_key_insights: int
    max_compressed_items: int
    enable_data_compression: bool
    keywords: Dict[str, list]
    required_roles: list

class BusinessCaseConfig(BaseModel):
    default: Dict[str, Any]

class ToolParameterConfig(BaseModel):
    template: str
    required: bool = True

class ToolConfig(BaseModel):
    name: str
    description: str
    function: str
    parameters: Dict[str, ToolParameterConfig]

class ToolsConfig(BaseModel):
    tavily_search: ToolConfig
    google_trends: ToolConfig
    google_maps: ToolConfig

class ModelConfig(BaseModel):
    model: str  # CHANGED: from model_name to model for consistency
    import_path: str
    api_key: str
    temperature: float
    max_tokens: int

class LLMsConfig(BaseModel):
    groq: ModelConfig
    mistral: ModelConfig
    openai: ModelConfig
    google: ModelConfig

class ModelsConfig(BaseModel):
    llms: LLMsConfig

class ReportingConfig(BaseModel):
    save_to_file: bool
    reports_directory: str
    create_backup: bool
    save_formats: list

class MonitoringConfig(BaseModel):
    langsmith: Dict[str, Any]

class StorageConfig(BaseModel):
    pinecone: Dict[str, str]
    aws: Dict[str, str]

class ConfigSchema(BaseModel):
    paths: PathsConfig
    app: AppConfig
    defaults: DefaultsConfig
    research: ResearchConfig
    apis: APIConfig
    export: ExportConfig
    analysis: AnalysisConfig
    business_case: BusinessCaseConfig
    tools: ToolsConfig
    models: ModelsConfig
    reporting: ReportingConfig
    monitoring: MonitoringConfig
    storage: StorageConfig


class ConfigLoader:
    """Central configuration manager for Restaurant Research System."""

    def __init__(self, env_path=".env", config_path="src/configuration/configs.yaml"):
        try:
            self.env_path = Path(env_path)
            self.config_path = Path(config_path)
            self._load_env()
            raw = self._load_yaml_with_env_override()
            raw = self._resolve_env_vars(raw)
            self.config = ConfigSchema(**raw)
            logger.info("Restaurant Research Configuration loaded successfully.")
        except (FileNotFoundError, Exception) as e:
            raise CustomException("Failed to initialize configuration", e)

    def _load_env(self):
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info(f"Environment variables loaded from {self.env_path}")

    def _load_yaml_with_env_override(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Missing config file: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            base = yaml.safe_load(f) or {}
        return base

    def _resolve_env_vars(self, data: Any) -> Any:
        """Resolve environment variables in configuration strings."""
        if isinstance(data, dict):
            return {k: self._resolve_env_vars(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._resolve_env_vars(v) for v in data]
        if isinstance(data, str):
            resolved_data = data
            for match in re.findall(r"\$\{([^}]+)\}", data):
                if ':-' in match:
                    var_name, default_value = match.split(':-', 1)
                else:
                    var_name, default_value = match, ""
                
                env_value = os.getenv(var_name)
                if env_value is not None:
                    resolved_data = resolved_data.replace(f"${{{match}}}", env_value)
                elif default_value:
                    resolved_data = resolved_data.replace(f"${{{match}}}", default_value)
                else:
                    logger.warning(f"Environment variable {var_name} not found and no default provided")
            
            # Handle simple ${VAR} format
            for match in re.findall(r"\$\{([^}:]+)\}", resolved_data):
                env_value = os.getenv(match)
                if env_value is not None:
                    resolved_data = resolved_data.replace(f"${{{match}}}", env_value)
                else:
                    logger.warning(f"Environment variable {match} not found")
            
            # Type conversion
            if resolved_data.isdigit():
                return int(resolved_data)
            elif resolved_data.replace('.', '').isdigit() and resolved_data.count('.') == 1:
                return float(resolved_data)
            elif resolved_data.lower() in ['true', 'false']:
                return resolved_data.lower() == 'true'
            
            return resolved_data
        return data

    def get(self, key: str = None, default: Any = None) -> Any:
        """Access nested configuration values using dot notation."""
        data = self.config.dict()
        if not key:
            return data
        
        keys = key.split(".")
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        """Get LLM configuration for specific provider."""
        return self.get(f"models.llms.{provider}", {})

    def get_api_keys(self) -> Dict[str, str]:
        """Extract all API keys from configuration."""
        api_keys = {}
        llms = self.get("models.llms", {})
        for provider, config in llms.items():
            if "api_key" in config and config["api_key"]:
                api_keys[provider.upper() + "_API_KEY"] = config["api_key"]
        return api_keys


# Singleton Instance
config_loader = ConfigLoader()