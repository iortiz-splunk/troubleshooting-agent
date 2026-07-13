"""Part 1 agent smoke tests."""

from unittest.mock import MagicMock

from part1_agent.agent import build_agent_graph
from workshop_shared.config import Settings


def test_part1_graph_compiles_without_tools() -> None:
    mock_llm = MagicMock()
    graph = build_agent_graph(mock_llm, [])
    app = graph.compile()
    assert app is not None
