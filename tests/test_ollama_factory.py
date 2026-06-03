"""Tests for Ollama LLM factory and health checks."""

from unittest.mock import MagicMock

import httpx

from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.ollama import (
    build_llm,
    check_ollama_health,
    is_configured_model_available,
)


def test_build_llm_uses_settings() -> None:
    settings = Settings(ollama_model="test-model", ollama_temperature=0.5)
    llm = build_llm(settings)
    assert llm.model == "test-model"
    assert llm.temperature == 0.5


def test_check_ollama_health_success() -> None:
    settings = Settings()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"models": [{"name": "llama3.2:3b"}]}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    ok, models, error = check_ollama_health(settings, client=mock_client)
    assert ok is True
    assert "llama3.2:3b" in models
    assert error is None


def test_check_ollama_health_failure() -> None:
    settings = Settings()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ConnectError("connection refused")

    ok, models, error = check_ollama_health(settings, client=mock_client)
    assert ok is False
    assert models == []
    assert error is not None


def test_is_configured_model_available() -> None:
    settings = Settings(ollama_model="llama3.2:3b")
    assert is_configured_model_available(settings, ["llama3.2:3b", "other:latest"])
    assert is_configured_model_available(settings, ["llama3.2:latest"])
