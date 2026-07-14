"""Register the active workshop part's run_chat for shared Slack integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from workshop_shared.config import Settings

RunChatFn = Callable[..., str]

_run_chat: RunChatFn | None = None


# ---------------------------------------------------------------------------
# Agent registration
# Each part registers its run_chat on CLI startup; Slack listener uses this indirection.
# ---------------------------------------------------------------------------
def register_run_chat(fn: RunChatFn) -> None:
    """Called by each part's CLI on startup to wire Slack -> that part's agent."""
    global _run_chat
    _run_chat = fn


def get_run_chat() -> RunChatFn:
    if _run_chat is None:
        msg = (
            "No agent registered. Run troubleshooting-agent from part1_agent/, "
            "part2_agent/, or part3_agent/."
        )
        raise RuntimeError(msg)
    return _run_chat


def run_chat(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
) -> str:
    """Delegate to the registered part agent."""
    return get_run_chat()(
        settings,
        user_message,
        investigation_id=investigation_id,
        source=source,
        investigation_metadata=investigation_metadata,
    )
