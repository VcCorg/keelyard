"""Tests for agent configuration."""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import AgentConfig


def test_default_config():
    config = AgentConfig()
    assert config.model_name == "gemini-2.5-flash-lite"
    assert config.max_proposals == 10
    assert config.auto_accept is False


def test_load_from_file(tmp_path):
    config_file = tmp_path / "agent.json"
    config_file.write_text(json.dumps({
        "model_name": "gemini-pro",
        "max_proposals": 5,
    }))
    config = AgentConfig.load(config_file)
    assert config.model_name == "gemini-pro"
    assert config.max_proposals == 5


def test_env_override(tmp_path, monkeypatch):
    config_file = tmp_path / "agent.json"
    config_file.write_text(json.dumps({"model_name": "gemini-pro"}))
    monkeypatch.setenv("ONBOARD_AGENT_MODEL", "custom-model")
    config = AgentConfig.load(config_file)
    assert config.model_name == "custom-model"


def test_missing_config_file(tmp_path):
    config = AgentConfig.load(tmp_path / "nonexistent.json")
    assert config.model_name == "gemini-2.5-flash-lite"
