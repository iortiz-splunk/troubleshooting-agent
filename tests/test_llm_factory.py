"""Tests for LLM factory."""

from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from workshop_shared.config import Settings
from workshop_shared.llm.factory import build_llm


@patch("workshop_shared.llm.factory.ChatOpenAI")
def test_build_llm_openai(mock_openai: MagicMock) -> None:
    settings = Settings(
        llm_provider="openai",
        openai_api_key="secret",
        openai_base_url="https://lite-llm-proxy.example.com/v1",
        openai_model_name="gpt-4.1-mini",
        llm_temperature=0.3,
    )
    build_llm(settings)
    mock_openai.assert_called_once_with(
        model="gpt-4.1-mini",
        api_key=SecretStr("secret"),
        base_url="https://lite-llm-proxy.example.com/v1",
        temperature=0.3,
    )


@patch("workshop_shared.llm.factory.AzureChatOpenAI")
def test_build_llm_azure(mock_azure: MagicMock) -> None:
    settings = Settings(
        llm_provider="azure_openai",
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="key",
        azure_openai_deployment_name="gpt-4o",
        azure_openai_api_version="2024-10-21",
        llm_temperature=0.3,
    )
    build_llm(settings)
    mock_azure.assert_called_once_with(
        azure_endpoint="https://test.openai.azure.com/",
        api_key=SecretStr("key"),
        azure_deployment="gpt-4o",
        api_version="2024-10-21",
        temperature=0.3,
    )


@patch("workshop_shared.llm.factory.ChatOllama")
def test_build_llm_ollama(mock_ollama: MagicMock) -> None:
    settings = Settings(ollama_model="test-model", llm_temperature=0.5)
    build_llm(settings)
    mock_ollama.assert_called_once_with(
        base_url=settings.ollama_base_url,
        model="test-model",
        temperature=0.5,
    )
