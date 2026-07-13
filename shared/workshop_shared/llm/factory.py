"""LLM factory — Ollama, OpenAI-compatible, or Azure OpenAI based on settings."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import SecretStr

from workshop_shared.config import Settings

# ---------------------------------------------------------------------------
# API key helper
# Wraps plain strings as SecretStr so keys are not logged by LangChain.
# ---------------------------------------------------------------------------


def _as_secret(value: str | None) -> SecretStr | None:
    return SecretStr(value) if value else None


# ---------------------------------------------------------------------------
# Provider selection
# settings.llm_provider picks Ollama (default), OpenAI-compatible, or Azure.
# ---------------------------------------------------------------------------


def build_llm(settings: Settings) -> BaseChatModel:
    """Create a chat model from settings."""
    if settings.llm_provider == "openai":
        return ChatOpenAI(
            model=settings.openai_model_name,
            api_key=_as_secret(settings.openai_api_key),
            base_url=settings.openai_base_url,
            temperature=settings.llm_temperature,
        )
    if settings.llm_provider == "azure_openai":
        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=_as_secret(settings.azure_openai_api_key),
            azure_deployment=settings.azure_openai_deployment_name,
            api_version=settings.azure_openai_api_version,
            temperature=settings.llm_temperature,
        )
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=settings.llm_temperature,
    )
