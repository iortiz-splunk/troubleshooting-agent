"""Tests for application settings."""

import pytest

from troubleshooting_agent.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "qwen2.5-coder:7b"
    assert settings.enable_splunk_o11y is False
    assert settings.splunk_o11y_tool_prefix == "o11y_"


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    settings = Settings()
    assert settings.ollama_model == "qwen2.5:7b"
    assert settings.ollama_base_url == "http://localhost:11434"


def test_enable_o11y_requires_credentials() -> None:
    with pytest.raises(ValueError, match="SPLUNK_O11Y"):
        Settings(enable_splunk_o11y=True)


def test_enable_splunk_cloud_mcp_requires_credentials() -> None:
    with pytest.raises(ValueError, match="SPLUNK_CLOUD_MCP"):
        Settings(enable_splunk_cloud_mcp=True)


def test_enable_splunk_mcp_requires_credentials() -> None:
    with pytest.raises(ValueError, match="SPLUNK_MCP"):
        Settings(enable_splunk_mcp=True)
