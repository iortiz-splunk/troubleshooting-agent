"""Tests for ReAct subgraph tool call limits."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from part1_agent.agent import build_react_subgraph


@tool
def echo_tool(text: str) -> str:
    """Echo input."""
    return text


@pytest.mark.asyncio
async def test_react_subgraph_skips_duplicate_tool_calls() -> None:
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=llm)
    llm.ainvoke = AsyncMock(
        side_effect=[
            AIMessage(
                content="",
                tool_calls=[{"name": "echo_tool", "args": {"text": "first"}, "id": "call-1"}],
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "echo_tool", "args": {"text": "second"}, "id": "call-2"}],
            ),
            AIMessage(content="finished"),
        ]
    )

    graph = build_react_subgraph(
        llm,
        [echo_tool],
        system_prompt="test",
        tool_call_limits={"echo_tool": 1},
    )
    app = graph.compile()
    result = await app.ainvoke({"messages": []})

    assert result["messages"][-1].content == "finished"
    assert llm.ainvoke.await_count == 3
    skipped = [
        message
        for message in result["messages"]
        if hasattr(message, "content") and "SKIPPED" in str(message.content)
    ]
    assert skipped
