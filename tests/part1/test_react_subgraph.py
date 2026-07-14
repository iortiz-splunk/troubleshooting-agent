"""Tests for Part 1 ReAct subgraph routing."""

from langchain_core.messages import AIMessage

from part1_agent.agent import _make_should_continue, build_react_subgraph
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.tools import tool


@tool
def echo_tool(text: str) -> str:
    """Echo input."""
    return text


def test_make_should_continue_uses_custom_tools_node_name() -> None:
    router = _make_should_continue("investigate_tools")
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "echo_tool", "args": {"text": "hi"}, "id": "call-1"}],
            )
        ]
    }
    assert router(state) == "investigate_tools"


def test_make_should_continue_ends_without_tool_calls() -> None:
    router = _make_should_continue("investigate_tools")
    state = {"messages": [AIMessage(content="done")]}
    assert router(state) == "__end__"


@pytest.mark.asyncio
async def test_react_subgraph_custom_node_names_route_to_tools() -> None:
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(
        side_effect=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "echo_tool", "args": {"text": "ping"}, "id": "call-1"},
                ],
            ),
            AIMessage(content="finished"),
        ]
    )

    graph = build_react_subgraph(
        llm,
        [echo_tool],
        system_prompt="test",
        llm_node_name="investigate_llm",
        tools_node_name="investigate_tools",
    )
    app = graph.compile()
    result = await app.ainvoke({"messages": []})

    assert result["messages"][-1].content == "finished"
    assert llm.ainvoke.await_count == 2
