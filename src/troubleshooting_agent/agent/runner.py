"""Invoke the troubleshooting agent and format output."""

from __future__ import annotations

import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool

from troubleshooting_agent.agent.graph import build_agent_graph
from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.ollama import build_llm
from troubleshooting_agent.mcp.session import McpSessionManager
from troubleshooting_agent.tools.base import get_tools


def run_chat(settings: Settings, user_message: str) -> str:
    """Run the agent graph with a single user message (sync entry point)."""
    return asyncio.run(_run_chat_async(settings, user_message))


async def _run_chat_async(settings: Settings, user_message: str) -> str:
    if (
        settings.enable_splunk_o11y
        or settings.enable_splunk_cloud_mcp
        or settings.enable_splunk_mcp
    ):
        async with McpSessionManager(settings) as mcp_manager:
            return await _invoke_agent(settings, user_message, mcp_manager.langchain_tools)
    return await _invoke_agent(settings, user_message, None)


def _format_ai_content(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p)
    return ""


def _last_tool_result(messages: list[BaseMessage]) -> str | None:
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            content = message.content
            if isinstance(content, str) and content.strip():
                if content.lstrip().startswith("ERROR:"):
                    return None
                return content
    return None


def _looks_like_tool_failure_summary(text: str) -> bool:
    lowered = text.lower()
    markers = (
        "issue with the",
        "required parameter",
        "tool loop is operational",
        "would you like me to proceed",
        "please provide",
    )
    return any(marker in lowered for marker in markers)


def _extract_final_response(messages: list[BaseMessage]) -> str:
    """
    Return the best final assistant message.

    Skips intermediate AIMessages that only requested tools, and prefers the
    last assistant reply after tool results.
    """
    tool_data = _last_tool_result(messages)

    last_tool_idx = -1
    for i, message in enumerate(messages):
        if isinstance(message, ToolMessage):
            last_tool_idx = i

    search_from = last_tool_idx + 1 if last_tool_idx >= 0 else 0
    for message in reversed(messages[search_from:]):
        if isinstance(message, AIMessage):
            text = _format_ai_content(message)
            if text.strip() and not message.tool_calls:
                if tool_data and _looks_like_tool_failure_summary(text):
                    return (
                        f"{text.strip()}\n\n--- Observability data ---\n{tool_data}"
                    )
                return text

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _format_ai_content(message)
            if text.strip():
                if tool_data and _looks_like_tool_failure_summary(text):
                    return (
                        f"{text.strip()}\n\n--- Observability data ---\n{tool_data}"
                    )
                return text

    if tool_data:
        return tool_data

    return "No response generated."


async def _invoke_agent(
    settings: Settings,
    user_message: str,
    mcp_tools: list[BaseTool] | None,
) -> str:
    llm = build_llm(settings)
    tools = get_tools(settings, mcp_tools=mcp_tools)
    graph = build_agent_graph(llm, tools)
    app = graph.compile()

    result = await app.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"recursion_limit": 25},
    )
    messages = result.get("messages", [])
    return _extract_final_response(messages)
