"""Smoke tests for agent graph (mocked LLM)."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from troubleshooting_agent.agent.graph import build_agent_graph
from troubleshooting_agent.agent.runner import run_chat
from troubleshooting_agent.config import Settings
from troubleshooting_agent.tools.base import get_tools


def test_build_agent_graph_compiles() -> None:
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    tools = get_tools(Settings())
    graph = build_agent_graph(mock_llm, tools)
    app = graph.compile()
    assert app is not None


@patch("troubleshooting_agent.agent.runner.build_llm")
@patch("troubleshooting_agent.agent.runner.get_tools")
def test_run_chat_returns_ai_message(
    mock_get_tools: MagicMock,
    mock_build_llm: MagicMock,
) -> None:
    mock_get_tools.return_value = []

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.return_value = AIMessage(content="Check load balancer health.")
    mock_build_llm.return_value = mock_llm

    settings = Settings()
    # Empty tools path: graph without tool node
    with patch("troubleshooting_agent.agent.runner.get_tools", return_value=[]):
        result = run_chat(settings, "Why 503?")
    assert "load balancer" in result.lower() or "503" in result or len(result) > 0
