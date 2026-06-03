"""Ollama LLM factory and health checks."""

from __future__ import annotations

import httpx
from langchain_ollama import ChatOllama

from troubleshooting_agent.config import Settings


def build_llm(settings: Settings) -> ChatOllama:
    """Create a ChatOllama instance from settings."""
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=settings.ollama_temperature,
    )


def check_ollama_health(
    settings: Settings,
    *,
    client: httpx.Client | None = None,
) -> tuple[bool, list[str], str | None]:
    """
    Verify Ollama is reachable and return available model names.

    Returns:
        (ok, model_names, error_message)
    """
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    own_client = client is None
    http = client or httpx.Client(timeout=10.0)
    try:
        response = http.get(url)
        response.raise_for_status()
        data = response.json()
        models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        return True, models, None
    except httpx.HTTPError as exc:
        return False, [], str(exc)
    finally:
        if own_client:
            http.close()


def is_configured_model_available(settings: Settings, model_names: list[str]) -> bool:
    """Return True if settings.ollama_model appears in the tag list."""
    target = settings.ollama_model
    if target in model_names:
        return True
    # Ollama may report names with :latest suffix
    return any(name.split(":")[0] == target.split(":")[0] for name in model_names)
