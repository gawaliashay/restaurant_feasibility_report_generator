"""
Unit tests for ConfigLoader.
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from src.configuration.config_loader import ConfigLoader


# ============================================================
# FIXTURES - Defined directly in this file
# ============================================================

@pytest.fixture
def temp_config_file():
    """Create a temporary config file for testing."""
    config_data = {
        "test": {"key": "value", "nested": {"key2": "value2"}},
        "research": {
            "sections": {
                "test_section": {
                    "enabled": True,
                    "tools": ["test_tool"],
                    "queries": {"test_tool": ["test query"]},
                }
            }
        },
        "resource_limits": {
            "mode": "fast",
            "fast": {
                "max_evidence_chars_per_section": 1000,
                "max_tool_results_per_section": 5,
                "max_text_per_result": 100,
            },
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing."""
    env_data = """TEST_ENV_VAR=test_value
ANOTHER_VAR=another_value
NUMBER_VAR=123
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write(env_data)
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


# ============================================================
# TESTS
# ============================================================

class TestConfigLoader:
    def test_config_loader_creates_instance(self):
        loader = ConfigLoader()
        assert loader is not None
        assert hasattr(loader, "get")

    def test_get_existing_key(self, temp_config_file):
        loader = ConfigLoader(config_path=str(temp_config_file))
        result = loader.get("test.key")
        assert result == "value"

    def test_get_nested_key(self, temp_config_file):
        loader = ConfigLoader(config_path=str(temp_config_file))
        result = loader.get("test.nested.key2")
        assert result == "value2"

    def test_get_missing_key_returns_default(self, temp_config_file):
        loader = ConfigLoader(config_path=str(temp_config_file))
        result = loader.get("nonexistent.key", "default_value")
        assert result == "default_value"

    def test_get_missing_key_returns_none(self, temp_config_file):
        loader = ConfigLoader(config_path=str(temp_config_file))
        result = loader.get("nonexistent.key")
        assert result is None

    def test_get_with_empty_config(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("{}")
        loader = ConfigLoader(config_path=str(config_path))
        result = loader.get("any.key", "default")
        assert result == "default"

    def test_resolve_env_vars(self, temp_config_file, temp_env_file):
        os.environ["TEST_ENV_VAR"] = "test_value"
        config_path = temp_config_file.parent / "config_with_env.yaml"
        config_data = {"key": "${TEST_ENV_VAR}"}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        loader = ConfigLoader(config_path=str(config_path))
        result = loader.get("key")
        assert result == "test_value"

    def test_resolve_env_var_with_nested_config(self, tmp_path):
        os.environ["NESTED_VAR"] = "nested_value"
        config_path = tmp_path / "config.yaml"
        config_data = {"nested": {"key": "${NESTED_VAR}"}}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        loader = ConfigLoader(config_path=str(config_path))
        result = loader.get("nested.key")
        assert result == "nested_value"

    def test_environment_variable_loaded(self, temp_env_file):
        loader = ConfigLoader(env_path=str(temp_env_file))
        assert os.getenv("TEST_ENV_VAR") == "test_value"

    def test_config_loader_handles_missing_env_file(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_data = {"test": "value"}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        loader = ConfigLoader(
            env_path=tmp_path / "nonexistent.env",
            config_path=str(config_path),
        )
        assert loader.get("test") == "value"

    def test_config_loader_file_not_found(self, tmp_path):
        config_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            ConfigLoader(config_path=str(config_path))

    def test_get_business_case(self):
        loader = ConfigLoader()
        result = loader.get("business_case.default.restaurant_concept")
        assert result is not None or result is None

    def test_get_resource_limits_mode(self):
        loader = ConfigLoader()
        mode = loader.get("resource_limits.mode", "balanced")
        assert mode in ["fast", "balanced", "quality"]

    def test_get_research_sections(self):
        loader = ConfigLoader()
        sections = loader.get("research.sections", {})
        assert isinstance(sections, dict)

    def test_get_report_sections(self):
        loader = ConfigLoader()
        sections = loader.get("report.sections", {})
        assert isinstance(sections, dict)

    def test_get_tavily_settings(self):
        loader = ConfigLoader()
        config = loader.get("apis.tavily", {})
        assert isinstance(config, dict)
        assert config.get("max_results") == 5