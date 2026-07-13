"""Azure OpenAI health checks (deprecated path — use invoke_health)."""

from __future__ import annotations

from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.invoke_health import (
    check_llm_invoke_health,
    check_llm_invoke_health_sync,
)


async def check_azure_openai_health(
    settings: Settings,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[bool, str | None]:
    """Verify Azure OpenAI is reachable with the configured deployment."""
    return await check_llm_invoke_health(settings, timeout_seconds=timeout_seconds)


def check_azure_openai_health_sync(
    settings: Settings,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[bool, str | None]:
    """Sync wrapper for CLI doctor."""
    return check_llm_invoke_health_sync(settings, timeout_seconds=timeout_seconds)
