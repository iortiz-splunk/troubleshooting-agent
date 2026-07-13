"""Tests for Ollama health checks."""

from unittest.mock import MagicMock

import httpx

from workshop_shared.config import Settings
from workshop_shared.llm.ollama import (
    check_ollama_health,
    is_configured_model_available,
)


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
