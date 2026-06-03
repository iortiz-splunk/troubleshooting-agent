"""Tests for tool registry."""

from troubleshooting_agent.config import Settings
from troubleshooting_agent.tools.base import get_tools
from troubleshooting_agent.tools.builtin import agent_health_check


def test_get_tools_includes_builtin() -> None:
    settings = Settings()
    tools = get_tools(settings)
    names = [t.name for t in tools]
    assert agent_health_check.name in names


def test_stub_tools_disabled_by_default() -> None:
    settings = Settings()
    tools = get_tools(settings)
    assert len(tools) == 1
