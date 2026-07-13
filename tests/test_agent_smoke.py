"""Smoke tests for agent graph (mocked LLM)."""

from unittest.mock import MagicMock, patch

from part1_agent.agent import build_agent_graph
from workshop_shared.config import Settings
from workshop_shared.tools.base import get_tools


def test_build_agent_graph_compiles() -> None:
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    tools = get_tools(Settings())
    graph = build_agent_graph(mock_llm, tools)
    app = graph.compile()
    assert app is not None


@patch("part3_agent.agent.asyncio.run")
def test_run_chat_returns_ai_message(mock_asyncio_run: MagicMock) -> None:
    from part3_agent.agent import run_chat

    mock_asyncio_run.return_value = "Check load balancer health."
    settings = Settings()
    result = run_chat(settings, "Why 503?")
    assert "load balancer" in result.lower()
