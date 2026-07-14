"""Part 3 agent: four-node graph with skills and full tool set."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool
from part1_agent.agent import _extract_final_response

from part3_agent.graph import build_part3_graph
from part3_agent.prompt import SYSTEM_PROMPT
from part3_agent.skill_router import build_system_prompt
from workshop_shared.config import Settings
from workshop_shared.llm.factory import build_llm
from workshop_shared.mcp.session import McpSessionManager
from workshop_shared.observability.galileo import (
    build_galileo_callback,
    finalize_galileo_session_tokens,
)
from workshop_shared.observability.logging_trace import (
    investigation_scope,
    log_agent_done,
    log_agent_response,
    log_agent_start,
    log_investigation_banner,
    log_skill_injected,
    new_chat_investigation_id,
)
from workshop_shared.observability.otel import span as otel_span
from workshop_shared.tools.base import get_tools


# ---------------------------------------------------------------------------
# Public entry point
# CLI and Slack call run_chat; Part 3 runs the four-node investigation graph.
# ---------------------------------------------------------------------------
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
    metadata = dict(investigation_metadata) if investigation_metadata else {}
    metadata.setdefault("workshop_part", "part3_agent")
    if source == "slack":
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


# ---------------------------------------------------------------------------
# Investigation runtime
# Compile Part 3 graph (identify → categorize → investigate → report).
# ---------------------------------------------------------------------------
def _build_runnable_config(
    settings: Settings,
    *,
    investigation_id: str,
    source: str,
    investigation_metadata: dict[str, str] | None,
) -> tuple[RunnableConfig, Any]:
    callbacks: list[Any] = []
    galileo_session = build_galileo_callback(
        settings,
        investigation_id=investigation_id,
        investigation_metadata=investigation_metadata,
    )
    if galileo_session is not None:
        callbacks.append(galileo_session.callback)

    metadata: dict[str, Any] = {
        "investigation_id": investigation_id,
        "source": source,
        "agent.graph": "part3",
    }
    if investigation_metadata:
        metadata.update(investigation_metadata)

    config = RunnableConfig(
        recursion_limit=30,
        callbacks=callbacks,
        metadata=metadata,
    )
    return config, galileo_session


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
    base_prompt, skill_names, routing = build_system_prompt(
        SYSTEM_PROMPT,
        investigation_metadata,
        alert_text,
    )

    enriched_metadata = dict(investigation_metadata) if investigation_metadata else {}
    enriched_metadata["workshop_part"] = "part3_agent"
    enriched_metadata["agent_graph"] = "part3"
    enriched_metadata["skill_router"] = routing.router
    if skill_names:
        enriched_metadata["skill"] = routing.domain_skill or skill_names[0]
        enriched_metadata["skills"] = ",".join(skill_names)
        enriched_metadata["skill_routing"] = routing.to_metadata_json()

    service = enriched_metadata.get("service") or (
        investigation_metadata.get("service") if investigation_metadata else None
    )
    environment = enriched_metadata.get("environment") or (
        investigation_metadata.get("environment") if investigation_metadata else None
    )

    log_investigation_banner(
        workshop_part="part3",
        source=source,
        query=user_message,
        provider=provider,
        mcp_tool_count=mcp_count,
        skill=skill_names[0] if skill_names else None,
        graph="identify → categorize → investigate → report",
        service=service,
        environment=environment,
    )
    log_agent_start(provider=provider, mcp_tool_count=mcp_count)
    for skill_name in skill_names:
        log_skill_injected(skill_name=skill_name)

    llm = build_llm(settings)
    graph = build_part3_graph(llm, tools, settings=settings, base_prompt=base_prompt)
    app = graph.compile(name="part3_investigation")
    config, galileo_session = _build_runnable_config(
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
        "agent.graph": "part3",
    }
    if skill_names:
        otel_attrs["agent.skill"] = skill_names[0]
    if investigation_metadata:
        if service := investigation_metadata.get("service"):
            otel_attrs["o11y.service"] = service
        if environment := investigation_metadata.get("environment"):
            otel_attrs["o11y.environment"] = environment

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_message)],
        "user_message": user_message,
        "investigation_metadata": enriched_metadata or None,
        "skills_loaded": list(skill_names),
    }

    with otel_span("agent.investigation", otel_attrs):
        result = await app.ainvoke(initial_state, config=config)
    finalize_galileo_session_tokens(galileo_session)

    messages = result.get("messages", [])
    final_report = result.get("final_report")
    if isinstance(final_report, str) and final_report.strip():
        log_agent_done(message_count=len(messages))
        log_agent_response(final_report)
        return final_report

    response = _extract_final_response(messages)
    log_agent_done(message_count=len(messages))
    log_agent_response(response)
    return response
