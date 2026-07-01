"""Invoke the troubleshooting agent and format output."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool

from troubleshooting_agent.agent.graph import build_agent_graph
from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.factory import build_llm
from troubleshooting_agent.mcp.session import McpSessionManager
from troubleshooting_agent.observability.galileo import build_galileo_callback
from troubleshooting_agent.observability.logging_trace import (
    investigation_scope,
    log_agent_done,
    log_agent_start,
    new_chat_investigation_id,
)
from troubleshooting_agent.observability.otel import span as otel_span
from troubleshooting_agent.tools.base import get_tools


def run_chat(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
) -> str:
    """Run the agent graph with a single user message (sync entry point)."""
    return asyncio.run(
        _run_chat_async(
            settings,
            user_message,
            investigation_id=investigation_id,
            source=source,
            investigation_metadata=investigation_metadata,
        )
    )


async def _run_chat_async(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
) -> str:
    inv_id = investigation_id or new_chat_investigation_id()
    with investigation_scope(settings, inv_id, metadata=investigation_metadata):
        if (
            settings.enable_splunk_o11y
            or settings.enable_splunk_cloud_mcp
            or settings.enable_splunk_mcp
        ):
            async with McpSessionManager(settings) as mcp_manager:
                return await _invoke_agent(
                    settings,
                    user_message,
                    mcp_manager.langchain_tools,
                    investigation_id=inv_id,
                    source=source,
                    investigation_metadata=investigation_metadata,
                )
        return await _invoke_agent(
            settings,
            user_message,
            None,
            investigation_id=inv_id,
            source=source,
            investigation_metadata=investigation_metadata,
        )


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
                    return f"{text.strip()}\n\n--- Observability data ---\n{tool_data}"
                return text

    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _format_ai_content(message)
            if text.strip():
                if tool_data and _looks_like_tool_failure_summary(text):
                    return f"{text.strip()}\n\n--- Observability data ---\n{tool_data}"
                return text

    if tool_data:
        return tool_data

    return "No response generated."


def _build_runnable_config(
    settings: Settings,
    *,
    investigation_id: str,
    source: str,
    investigation_metadata: dict[str, str] | None,
) -> RunnableConfig:
    callbacks: list[Any] = []
    galileo_cb = build_galileo_callback(settings)
    if galileo_cb is not None:
        callbacks.append(galileo_cb)

    metadata: dict[str, Any] = {
        "investigation_id": investigation_id,
        "source": source,
    }
    if investigation_metadata:
        metadata.update(investigation_metadata)

    return RunnableConfig(
        recursion_limit=25,
        callbacks=callbacks,
        metadata=metadata,
    )


async def _invoke_agent(
    settings: Settings,
    user_message: str,
    mcp_tools: list[BaseTool] | None,
    *,
    investigation_id: str,
    source: str,
    investigation_metadata: dict[str, str] | None,
) -> str:
    provider = settings.llm_provider or "ollama"
    mcp_count = len(mcp_tools) if mcp_tools else 0
    log_agent_start(provider=provider, mcp_tool_count=mcp_count)

    llm = build_llm(settings)
    tools = get_tools(settings, mcp_tools=mcp_tools)
    graph = build_agent_graph(llm, tools)
    app = graph.compile()
    config = _build_runnable_config(
        settings,
        investigation_id=investigation_id,
        source=source,
        investigation_metadata=investigation_metadata,
    )

    otel_attrs: dict[str, Any] = {
        "agent.investigation_id": investigation_id,
        "llm.provider": provider,
        "mcp.tool_count": mcp_count,
        "agent.source": source,
    }
    if investigation_metadata:
        if service := investigation_metadata.get("service"):
            otel_attrs["o11y.service"] = service
        if environment := investigation_metadata.get("environment"):
            otel_attrs["o11y.environment"] = environment

    with otel_span("agent.investigation", otel_attrs):
        result = await app.ainvoke(
            {"messages": [HumanMessage(content=user_message)]},
            config=config,
        )
    messages = result.get("messages", [])
    log_agent_done(message_count=len(messages))
    return _extract_final_response(messages)
