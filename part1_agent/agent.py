"""Part 1 agent: minimal LangGraph ReAct loop with MCP tools only."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from part1_agent.prompt import SYSTEM_PROMPT
from workshop_shared.config import Settings
from workshop_shared.llm.factory import build_llm
from workshop_shared.mcp.session import McpSessionManager
from workshop_shared.observability.galileo import (
    build_galileo_callback,
    finalize_galileo_session_tokens,
    log_skill_router_to_galileo,
)
from workshop_shared.observability.logging_trace import (
    investigation_scope,
    log_agent_done,
    log_agent_response,
    log_agent_start,
    log_investigation_banner,
    log_llm_turn,
    log_skill_injected,
    new_chat_investigation_id,
    preview,
)
from workshop_shared.observability.otel import span as otel_span
from workshop_shared.tool_calls import ensure_ai_tool_calls


# ---------------------------------------------------------------------------
# Graph state
# Message list passed between LangGraph nodes; add_messages merges turns.
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _make_should_continue(tools_node_name: str):
    """Route to the configured tools node when the model emits tool calls."""

    def should_continue(state: AgentState) -> Literal["__end__"] | str:
        messages = state["messages"]
        if not messages:
            return "__end__"
        last = messages[-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return tools_node_name
        return "__end__"

    return should_continue


# ---------------------------------------------------------------------------
# LangGraph ReAct loop
# agent node (LLM) -> tools node -> agent until the model stops calling tools.
# Part 2 reuses build_agent_graph; Part 3 uses build_react_subgraph with custom names.
# ---------------------------------------------------------------------------
def build_react_subgraph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    *,
    system_prompt: str = SYSTEM_PROMPT,
    llm_node_name: str = "agent",
    tools_node_name: str = "tools",
) -> StateGraph[AgentState, None, AgentState, AgentState]:
    """Build a ReAct loop with configurable node names for nested tracing."""
    tools_by_name = {t.name: t for t in tools}
    if tools:
        model = llm.bind_tools(tools)
        model_force_tools = llm.bind_tools(tools, tool_choice="required")
    else:
        model = llm
        model_force_tools = None

    tool_node = ToolNode(tools) if tools else None

    async def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
        messages = list(state["messages"])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt), *messages]
        has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
        invoke_model = model_force_tools if model_force_tools and not has_tool_results else model
        with otel_span("agent.llm.turn", {"agent.subgraph_node": llm_node_name}):
            response = await invoke_model.ainvoke(messages)
        if isinstance(response, AIMessage):
            response = ensure_ai_tool_calls(response, tools_by_name=tools_by_name)
            if response.tool_calls:
                tool_names = [
                    str(tc.get("name", ""))
                    for tc in response.tool_calls
                    if isinstance(tc, dict) and tc.get("name")
                ]
                log_llm_turn(tool_names=tool_names, final_chars=None)
            else:
                content = response.content
                chars = len(content) if isinstance(content, str) else 0
                log_llm_turn(tool_names=None, final_chars=chars)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node(llm_node_name, call_model)
    if tool_node is not None:
        graph.add_node(tools_node_name, tool_node)
        graph.set_entry_point(llm_node_name)
        graph.add_conditional_edges(
            llm_node_name,
            _make_should_continue(tools_node_name),
            {tools_node_name: tools_node_name, "__end__": END},
        )
        graph.add_edge(tools_node_name, llm_node_name)
    else:
        graph.set_entry_point(llm_node_name)
        graph.add_edge(llm_node_name, END)
    return graph


def build_agent_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    *,
    system_prompt: str = SYSTEM_PROMPT,
) -> StateGraph[AgentState, None, AgentState, AgentState]:
    """Build a ReAct loop: agent -> tools -> agent until no tool calls."""
    return build_react_subgraph(llm, tools, system_prompt=system_prompt)


def _mcp_tools_only(mcp_tools: list[BaseTool] | None) -> list[BaseTool]:
    return list(mcp_tools) if mcp_tools else []


# ---------------------------------------------------------------------------
# Public entry point
# CLI and Slack call run_chat; opens MCP session when integrations are enabled.
# ---------------------------------------------------------------------------
def run_chat(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
    system_prompt: str | None = None,
) -> str:
    return asyncio.run(
        _run_chat_async(
            settings,
            user_message,
            investigation_id=investigation_id,
            source=source,
            investigation_metadata=investigation_metadata,
            system_prompt=system_prompt or SYSTEM_PROMPT,
        )
    )


async def _run_chat_async(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    inv_id = investigation_id or new_chat_investigation_id()
    metadata = dict(investigation_metadata) if investigation_metadata else {}
    metadata.setdefault("workshop_part", "part1_agent")
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
                    system_prompt=system_prompt,
                )
        return await _invoke_agent(
            settings,
            user_message,
            None,
            investigation_id=inv_id,
            source=source,
            investigation_metadata=metadata,
            system_prompt=system_prompt,
        )


# ---------------------------------------------------------------------------
# Response extraction
# Pick the final user-facing text from the message history after the graph run.
# ---------------------------------------------------------------------------
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
    """True when the model gave a thin failure message instead of using tool results."""
    lowered = text.lower()
    if len(text.strip()) > 600:
        return False
    markers = (
        "issue with the",
        "required parameter",
        "tool loop is operational",
        "please provide",
    )
    return any(marker in lowered for marker in markers)


def _tool_data_fallback(text: str, tool_data: str) -> str:
    """Append a short observability excerpt only for thin failure summaries."""
    excerpt = preview(tool_data, limit=1200)
    return f"{text.strip()}\n\n--- Observability data ---\n{excerpt}"


def _extract_final_response(messages: list[BaseMessage]) -> str:
    tool_data = _last_tool_result(messages)
    last_tool_idx = max(
        (i for i, m in enumerate(messages) if isinstance(m, ToolMessage)),
        default=-1,
    )
    search_from = last_tool_idx + 1 if last_tool_idx >= 0 else 0
    for message in reversed(messages[search_from:]):
        if isinstance(message, AIMessage):
            text = _format_ai_content(message)
            if text.strip() and not message.tool_calls:
                if tool_data and _looks_like_tool_failure_summary(text):
                    return _tool_data_fallback(text, tool_data)
                return text
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _format_ai_content(message)
            if text.strip():
                if tool_data and _looks_like_tool_failure_summary(text):
                    return _tool_data_fallback(text, tool_data)
                return text
    if tool_data:
        return tool_data
    return "No response generated."


# ---------------------------------------------------------------------------
# Investigation runtime
# Wire LLM, graph, Galileo callbacks, and OTel for a single investigation.
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
    }
    if investigation_metadata:
        metadata.update(investigation_metadata)

    config = RunnableConfig(
        recursion_limit=25,
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
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    provider = settings.llm_provider or "ollama"
    tools = _mcp_tools_only(mcp_tools)
    mcp_count = len(tools)

    meta = investigation_metadata or {}
    workshop_part = meta.get("workshop_part", "part1_agent")
    service = meta.get("service")
    environment = meta.get("environment")
    skill = meta.get("skill")
    graph = meta.get("agent_graph")

    log_investigation_banner(
        workshop_part=workshop_part,
        source=source,
        query=user_message,
        provider=provider,
        mcp_tool_count=mcp_count,
        skill=skill,
        graph=graph,
        service=service,
        environment=environment,
    )
    log_agent_start(provider=provider, mcp_tool_count=mcp_count)
    loaded_skills = [
        name.strip() for name in (meta.get("skills") or "").split(",") if name.strip()
    ]
    for skill_name in loaded_skills:
        log_skill_injected(skill_name=skill_name)

    llm = build_llm(settings)
    graph = build_agent_graph(llm, tools, system_prompt=system_prompt)
    app = graph.compile()
    config, galileo_session = _build_runnable_config(
        settings,
        investigation_id=investigation_id,
        source=source,
        investigation_metadata=investigation_metadata,
    )

    if galileo_session is not None:
        log_skill_router_to_galileo(
            galileo_session.logger,
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
    finalize_galileo_session_tokens(galileo_session)
    messages = result.get("messages", [])
    response = _extract_final_response(messages)
    log_agent_done(message_count=len(messages))
    log_agent_response(response)
    return response
