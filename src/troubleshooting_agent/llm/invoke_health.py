"""Shared health check for remote chat models (OpenAI-compatible, Azure, etc.)."""

from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage

from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.factory import build_llm


async def check_llm_invoke_health(
    settings: Settings,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[bool, str | None]:
    """
    Verify the configured chat model responds to a minimal request.

    Returns:
        (ok, error_message)
    """
    try:
        llm = build_llm(settings)
        await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="ping")]),
            timeout=timeout_seconds,
        )
        return True, None
    except TimeoutError:
        return False, f"LLM request timed out after {timeout_seconds}s"
    except Exception as exc:
        return False, str(exc)


def check_llm_invoke_health_sync(
    settings: Settings,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[bool, str | None]:
    """Sync wrapper for CLI doctor."""
    return asyncio.run(check_llm_invoke_health(settings, timeout_seconds=timeout_seconds))
