"""Built-in tools for Phase 0."""

from langchain_core.tools import BaseTool, tool


@tool
def agent_health_check() -> str:
    """
    Confirm the agent tool loop is working.

    Use when you need to verify tool invocation before answering the user.
    """
    return "Agent tool loop is operational."


def get_tools() -> list[BaseTool]:
    """Return built-in tools available in Phase 0."""
    return [agent_health_check]
