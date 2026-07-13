"""Part 3 agent: full tooling + troubleshoot orchestration skill."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool

from part1_agent.agent import (
    _extract_final_response,
    build_agent_graph,
)
from part3_agent.prompt import SYSTEM_PROMPT
from part3_agent.skill_router import build_system_prompt
from workshop_shared.config import Settings
from workshop_shared.llm.factory import build_llm
from workshop_shared.mcp.session import McpSessionManager
from workshop_shared.observability.galileo import build_galileo_callback
from workshop_shared.observability.logging_trace import (
    investigation_scope,
    log_agent_done,
    log_agent_start,
    new_chat_investigation_id,
)
from workshop_shared.observability.otel import span as otel_span
from workshop_shared.tools.base import get_tools


def run_chat(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
) -> str:
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
    metadata = dict(investigation_metadata) if investigation_metadata else None
    if source == "slack" and metadata is not None:
        from workshop_shared.slack.alert_resolve import enrich_alert_context

        metadata = await enrich_alert_context(settings, metadata)

    with investigation_scope(settings, inv_id, metadata=metadata):
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
                    investigation_metadata=metadata,
                )
        return await _invoke_agent(
            settings,
            user_message,
            None,
            investigation_id=inv_id,
            source=source,
            investigation_metadata=metadata,
        )


def _build_runnable_config(
    settings: Settings,
    *,
    investigation_id: str,
    source: str,
    investigation_metadata: dict[str, str] | None,
) -> RunnableConfig:
    callbacks: list[Any] = []
    galileo_cb = build_galileo_callback(
        settings,
        investigation_id=investigation_id,
        investigation_metadata=investigation_metadata,
    )
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
    tools = get_tools(settings, mcp_tools=mcp_tools)
    mcp_count = len(mcp_tools) if mcp_tools else 0

    alert_text = user_message if source == "slack" else ""
    system_prompt, skill_names = build_system_prompt(
        SYSTEM_PROMPT,
        investigation_metadata,
        alert_text,
    )

    enriched_metadata = dict(investigation_metadata) if investigation_metadata else {}
    if skill_names:
        enriched_metadata["skill"] = skill_names[0]
        enriched_metadata["skills"] = ",".join(skill_names)

    log_agent_start(provider=provider, mcp_tool_count=mcp_count)

    llm = build_llm(settings)
    graph = build_agent_graph(llm, tools, system_prompt=system_prompt)
    app = graph.compile()
    config = _build_runnable_config(
        settings,
        investigation_id=investigation_id,
        source=source,
        investigation_metadata=enriched_metadata or None,
    )

    otel_attrs: dict[str, Any] = {
        "agent.investigation_id": investigation_id,
        "llm.provider": provider,
        "mcp.tool_count": mcp_count,
        "agent.source": source,
    }
    if skill_names:
        otel_attrs["agent.skill"] = skill_names[0]
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
