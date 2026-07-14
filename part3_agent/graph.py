"""Part 3 four-node LangGraph: identify → categorize → investigate → report."""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from part1_agent.agent import build_react_subgraph
from typing_extensions import TypedDict

from part3_agent.prompt import SYSTEM_PROMPT
from part3_agent.skill_categorizer import categorize_alert
from part3_agent.skill_router import ENTRY_SKILL_NAME
from part3_agent.skill_tools import format_skill_for_prompt, load_skill_content
from workshop_shared.config import Settings
from workshop_shared.observability.logging_trace import (
    log_node_enter,
    log_node_exit,
    log_node_snapshot,
    log_skill_injected,
)
from workshop_shared.observability.otel import span as otel_span
from workshop_shared.observability.skill_span import emit_skill_load
from workshop_shared.slack.alert_resolve import fetch_alert_payload


_logger = logging.getLogger(__name__)
INVESTIGATE_RECURSION_LIMIT = 25

# ---------------------------------------------------------------------------
# Graph state
# Workflow fields plus message history for observability and report output.
# ---------------------------------------------------------------------------
class Part3State(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_message: str
    investigation_metadata: dict[str, str] | None
    alert_payload: dict[str, Any] | None
    alert_load_error: str | None
    product_type: str | None
    skill_name: str | None
    investigation_summary: str | None
    skills_loaded: list[str]
    skip_investigate: bool
    final_report: str | None


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


def _last_ai_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            text = _format_ai_content(message)
            if text.strip():
                return text
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _format_ai_content(message)
            if text.strip():
                return text
    return ""


def _alert_summary(alert: dict[str, Any] | None) -> str:
    if not alert:
        return "No alert payload loaded."
    try:
        return json.dumps(alert, indent=2, default=str)[:8000]
    except TypeError:
        return str(alert)[:8000]


def _alert_mcp_params(
    alert: dict[str, Any] | None,
    investigation_metadata: dict[str, str] | None,
) -> dict[str, str]:
    """Extract service_name and environment_name for APM MCP tool params."""
    service = ""
    environment = ""
    if alert:
        props = alert.get("customProperties")
        if isinstance(props, dict):
            service = str(props.get("sf_service") or "").strip()
            environment = str(props.get("sf_environment") or "").strip()
        if not service:
            service = str(alert.get("sf_service") or "").strip()
        if not environment:
            environment = str(alert.get("sf_environment") or "").strip()
    meta = investigation_metadata or {}
    if not service:
        service = str(meta.get("service") or "").strip()
    if not environment:
        environment = str(meta.get("environment") or "").strip()
    return {"service_name": service, "environment_name": environment}


def _investigate_user_content(
    *,
    user_text: str,
    alert: dict[str, Any] | None,
    investigation_metadata: dict[str, str] | None,
    product_type: str | None,
) -> str:
    alert_text = _alert_summary(alert)
    mcp_params = _alert_mcp_params(alert, investigation_metadata)
    hints = ""
    if product_type == "apm" and (mcp_params["service_name"] or mcp_params["environment_name"]):
        exemplar_hint = (
            "For latency alerts use params.exemplar_type=`lat_buck_` "
            "(exact literal with trailing underscore). "
            "Other valid values: `req`, `err`, `rc_err`."
        )
        hints = (
            "\n\nRequired APM MCP params (use in every o11y_get_apm_* call):\n"
            f"- params.service_name: {mcp_params['service_name'] or '(unknown)'}\n"
            f"- params.environment_name: {mcp_params['environment_name'] or '(unknown)'}\n"
            f"- {exemplar_hint}\n"
            "If a tool returns a validation error, fix the param and retry once; "
            "then continue with other tools and summarize."
        )
    return (
        f"Investigate this alert.\n\nUser request:\n{user_text}\n\n"
        f"Alert payload:\n{alert_text}{hints}"
    )


def _recursion_limit_summary(
    *,
    product_type: str | None,
    alert: dict[str, Any] | None,
    limit: int,
) -> str:
    mcp_params = _alert_mcp_params(alert, None)
    return (
        f"Investigation incomplete: reached the {limit}-step tool loop limit "
        f"for product_type={product_type or 'unknown'}. "
        "Summarize any latency/error metrics already gathered. "
        f"Service={mcp_params['service_name'] or 'unknown'}, "
        f"environment={mcp_params['environment_name'] or 'unknown'}. "
        "If exemplar traces failed, note that params.exemplar_type must be "
        "exactly one of: req, err, rc_err, lat_buck_."
    )


def _node_config(
    config: RunnableConfig | None,
    node: str,
    state: Part3State,
) -> RunnableConfig:
    base: dict[str, Any] = dict(config or {})
    metadata = dict(base.get("metadata") or {})
    metadata["agent.node"] = node
    if state.get("product_type"):
        metadata["agent.product_type"] = state["product_type"]
    skills = state.get("skills_loaded") or []
    if skills:
        metadata["agent.skills_loaded"] = ",".join(skills)

    return RunnableConfig(
        **{
            **base,
            "metadata": metadata,
            "run_name": node,
        }
    )


def _entry_skill_chars(state: Part3State) -> int | None:
    meta = state.get("investigation_metadata") or {}
    raw = meta.get("skill_routing")
    if not raw:
        return None
    try:
        routing = json.loads(raw)
    except json.JSONDecodeError:
        return None
    chars = routing.get("chars_by_skill") or {}
    value = chars.get(ENTRY_SKILL_NAME)
    return int(value) if isinstance(value, int) else None


def _append_skill_loaded(state: Part3State, skill_name: str) -> list[str]:
    loaded = list(state.get("skills_loaded") or [])
    if skill_name not in loaded:
        loaded.append(skill_name)
    return loaded


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_part3_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    *,
    settings: Settings,
    base_prompt: str = SYSTEM_PROMPT,
) -> StateGraph[Part3State, None, Part3State, Part3State]:
    get_alerts_skill = format_skill_for_prompt("get-alerts-or-incidents")
    report_skill = format_skill_for_prompt("troubleshoot-report")
    get_alerts_chars = len(get_alerts_skill)
    report_chars = len(report_skill)

    identify_prompt = (
        f"{base_prompt}\n\n## Identify alert (step 1)\n\n"
        f"Load the alert payload using MCP tools. Follow this playbook:\n\n{get_alerts_skill}"
    )
    identify_subgraph = build_react_subgraph(
        llm,
        tools,
        system_prompt=identify_prompt,
        llm_node_name="identify_llm",
        tools_node_name="identify_tools",
    ).compile()

    def _investigate_prompt(skill_name: str) -> str:
        playbook = load_skill_content(skill_name) or ""
        return (
            f"{base_prompt}\n\n## Investigate (step 3)\n\n"
            f"Product playbook ({skill_name}):\n\n{playbook}\n\n"
            "Use MCP tools to gather evidence and summarize findings."
        )

    async def identify_node(state: Part3State, config: RunnableConfig) -> dict[str, Any]:
        node = "identify"
        node_config = _node_config(config, node, state)
        log_node_enter(node=node)

        if ENTRY_SKILL_NAME in (state.get("skills_loaded") or []):
            await emit_skill_load(
                node_config,
                skill_name=ENTRY_SKILL_NAME,
                role="graph_entry",
                chars=_entry_skill_chars(state),
                detail="preloaded into base system prompt",
            )

        await emit_skill_load(
            node_config,
            skill_name="get-alerts-or-incidents",
            role="identify",
            chars=get_alerts_chars,
            detail="preloaded into identify subgraph system prompt",
        )

        updates: dict[str, Any] = {
            "skills_loaded": _append_skill_loaded(state, "get-alerts-or-incidents"),
        }
        log_skill_injected(skill_name="get-alerts-or-incidents")

        with otel_span(f"agent.node.{node}", {"agent.node": node}):
            context = dict(state.get("investigation_metadata") or {})
            alert, error = await fetch_alert_payload(settings, context)
            if alert is not None:
                updates["alert_payload"] = alert
                updates["alert_load_error"] = None
            else:
                updates["alert_load_error"] = error
                user_text = state.get("user_message") or ""
                sub_result = await identify_subgraph.ainvoke(
                    {
                        "messages": [
                            HumanMessage(
                                content=(
                                    "Find the alert/incident for this investigation. "
                                    f"Context metadata: {json.dumps(context)}\n\n"
                                    f"User message:\n{user_text}"
                                )
                            )
                        ]
                    },
                    config=RunnableConfig(
                        **{
                            **dict(node_config),
                            "recursion_limit": 8,
                        }
                    ),
                )
                sub_messages = sub_result.get("messages", [])
                updates["messages"] = sub_messages
                retry_text = _last_ai_text(sub_messages)
                if retry_text:
                    context_with_summary = {**context, "identify_retry_summary": retry_text[:2000]}
                    alert, retry_error = await fetch_alert_payload(settings, context_with_summary)
                    if alert is not None:
                        updates["alert_payload"] = alert
                        updates["alert_load_error"] = None
                    elif retry_error and not updates.get("alert_load_error"):
                        updates["alert_load_error"] = retry_error

        log_node_exit(node=node, alert_found=str(bool(updates.get("alert_payload"))))
        log_node_snapshot(
            node=node,
            phase="exit",
            investigation_metadata=state.get("investigation_metadata"),
            alert_payload=updates.get("alert_payload"),
            alert_load_error=updates.get("alert_load_error"),
        )
        return updates

    async def categorize_node(state: Part3State, config: RunnableConfig) -> dict[str, Any]:
        node = "categorize"
        node_config = _node_config(config, node, state)
        log_node_enter(node=node)
        with otel_span(f"agent.node.{node}", {"agent.node": node}):
            result = categorize_alert(state.get("alert_payload"))
            skip = result.product_type == "unknown" or result.skill_name is None
        selected_skill = result.skill_name or "(none)"
        await emit_skill_load(
            node_config,
            skill_name=selected_skill,
            role="route",
            detail=f"product_type={result.product_type}",
        )
        if result.skill_name:
            log_skill_injected(skill_name=result.skill_name)
        log_node_exit(node=node, product_type=result.product_type)
        log_node_snapshot(
            node=node,
            phase="exit",
            investigation_metadata=state.get("investigation_metadata"),
            alert_payload=state.get("alert_payload"),
            product_type=result.product_type,
            skill_name=result.skill_name,
        )
        return {
            "product_type": result.product_type,
            "skill_name": result.skill_name,
            "skip_investigate": skip,
        }

    async def investigate_node(state: Part3State, config: RunnableConfig) -> dict[str, Any]:
        node = "investigate"
        log_node_enter(node=node, product_type=state.get("product_type"))
        updates: dict[str, Any] = {}

        if state.get("skip_investigate") or not state.get("skill_name"):
            summary = (
                "Investigation skipped: could not categorize alert to a product workflow. "
                f"Alert load error: {state.get('alert_load_error') or 'none'}"
            )
            log_node_exit(node=node, skipped="true")
            return {"investigation_summary": summary}

        skill_name = state["skill_name"]
        assert skill_name is not None
        skills_loaded = _append_skill_loaded(state, skill_name)
        updates["skills_loaded"] = skills_loaded

        node_config = _node_config(
            config,
            node,
            {**state, "skills_loaded": skills_loaded},
        )
        playbook_chars = len(load_skill_content(skill_name) or "")
        await emit_skill_load(
            node_config,
            skill_name=skill_name,
            role="investigate",
            chars=playbook_chars,
            detail=f"product_type={state.get('product_type')}",
        )
        log_skill_injected(skill_name=skill_name)

        prompt = _investigate_prompt(skill_name)
        investigate_subgraph = build_react_subgraph(
            llm,
            tools,
            system_prompt=prompt,
            llm_node_name="investigate_llm",
            tools_node_name="investigate_tools",
        ).compile()

        user_text = state.get("user_message") or ""
        investigate_content = _investigate_user_content(
            user_text=user_text,
            alert=state.get("alert_payload"),
            investigation_metadata=state.get("investigation_metadata"),
            product_type=state.get("product_type"),
        )
        log_node_snapshot(
            node=node,
            phase="enter",
            investigation_metadata=state.get("investigation_metadata"),
            alert_payload=state.get("alert_payload"),
            product_type=state.get("product_type"),
            skill_name=skill_name,
            user_message_preview=user_text[:500],
        )

        with otel_span(
            f"agent.node.{node}",
            {"agent.node": node, "agent.product_type": state.get("product_type") or ""},
        ):
            sub_config = RunnableConfig(
                **{
                    **dict(node_config),
                    "recursion_limit": INVESTIGATE_RECURSION_LIMIT,
                }
            )
            try:
                sub_result = await investigate_subgraph.ainvoke(
                    {"messages": [HumanMessage(content=investigate_content)]},
                    config=sub_config,
                )
                sub_messages = sub_result.get("messages", [])
                updates["messages"] = sub_messages
                updates["investigation_summary"] = (
                    _last_ai_text(sub_messages) or "No investigation output."
                )
            except GraphRecursionError:
                _logger.warning(
                    "investigate hit recursion_limit=%s for product_type=%s",
                    INVESTIGATE_RECURSION_LIMIT,
                    state.get("product_type"),
                )
                updates["investigation_summary"] = _recursion_limit_summary(
                    product_type=state.get("product_type"),
                    alert=state.get("alert_payload"),
                    limit=INVESTIGATE_RECURSION_LIMIT,
                )

        log_node_exit(node=node, product_type=state.get("product_type"))
        log_node_snapshot(
            node=node,
            phase="exit",
            investigation_metadata=state.get("investigation_metadata"),
            alert_payload=state.get("alert_payload"),
            product_type=state.get("product_type"),
            investigation_summary_preview=(updates.get("investigation_summary") or "")[:1000],
        )
        return updates

    async def report_node(state: Part3State, config: RunnableConfig) -> dict[str, Any]:
        node = "report"
        skills_loaded = _append_skill_loaded(state, "troubleshoot-report")
        node_config = _node_config(
            config,
            node,
            {**state, "skills_loaded": skills_loaded},
        )
        log_node_enter(node=node, product_type=state.get("product_type"))
        await emit_skill_load(
            node_config,
            skill_name="troubleshoot-report",
            role="report",
            chars=report_chars,
            detail="preloaded into report node system prompt",
        )
        log_skill_injected(skill_name="troubleshoot-report")

        report_prompt = (
            f"{base_prompt}\n\n## Report (step 4)\n\n"
            f"Format the final report using this playbook:\n\n{report_skill}"
        )

        alert_text = _alert_summary(state.get("alert_payload"))
        investigation = state.get("investigation_summary") or "No investigation was run."
        load_error = state.get("alert_load_error")
        log_node_snapshot(
            node=node,
            phase="enter",
            investigation_metadata=state.get("investigation_metadata"),
            alert_payload=state.get("alert_payload"),
            product_type=state.get("product_type"),
            investigation_summary_preview=investigation[:1000],
        )

        with otel_span(f"agent.node.{node}", {"agent.node": node}):
            response = await llm.ainvoke(
                [
                    SystemMessage(content=report_prompt),
                    HumanMessage(
                        content=(
                            f"Produce the final troubleshoot-report.\n\n"
                            f"Product type: {state.get('product_type') or 'unknown'}\n"
                            f"Alert load error: {load_error or 'none'}\n\n"
                            f"Alert payload:\n{alert_text}\n\n"
                            f"Investigation summary:\n{investigation}"
                        )
                    ),
                ],
                config=node_config,
            )

        if isinstance(response, AIMessage):
            final_report = _format_ai_content(response)
        else:
            final_report = str(response)
        log_node_exit(node=node, product_type=state.get("product_type"))
        log_node_snapshot(
            node=node,
            phase="exit",
            investigation_metadata=state.get("investigation_metadata"),
            alert_payload=state.get("alert_payload"),
            product_type=state.get("product_type"),
            final_report_preview=final_report[:1000],
        )
        return {
            "skills_loaded": skills_loaded,
            "final_report": final_report,
            "messages": [response],
        }

    graph = StateGraph(Part3State)
    graph.add_node("identify", identify_node, metadata={"agent.node": "identify"})
    graph.add_node("categorize", categorize_node, metadata={"agent.node": "categorize"})
    graph.add_node("investigate", investigate_node, metadata={"agent.node": "investigate"})
    graph.add_node("report", report_node, metadata={"agent.node": "report"})
    graph.add_edge(START, "identify")
    graph.add_edge("identify", "categorize")
    graph.add_edge("categorize", "investigate")
    graph.add_edge("investigate", "report")
    graph.add_edge("report", END)
    return graph
