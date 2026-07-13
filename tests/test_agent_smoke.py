"""Smoke tests for agent graph (mocked LLM)."""

from unittest.mock import MagicMock, patch

from troubleshooting_agent.agent.graph import build_agent_graph
from troubleshooting_agent.config import Settings
from troubleshooting_agent.tools.base import get_tools


def test_build_agent_graph_compiles() -> None:
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    tools = get_tools(Settings())
    graph = build_agent_graph(mock_llm, tools)
    app = graph.compile()
    assert app is not None


@patch("troubleshooting_agent.agent.runner.asyncio.run")
def test_run_chat_returns_ai_message(mock_asyncio_run: MagicMock) -> None:
    from troubleshooting_agent.agent.runner import run_chat

    mock_asyncio_run.return_value = "Check load balancer health."
    settings = Settings()
    result = run_chat(settings, "Why 503?")
    assert "load balancer" in result.lower()
