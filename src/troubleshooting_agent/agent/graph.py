"""LangGraph agent with tool-calling loop."""

from __future__ import annotations

from typing import Annotated, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from troubleshooting_agent.agent.tool_calls import ensure_ai_tool_calls
from troubleshooting_agent.observability.logging_trace import log_llm_turn
from troubleshooting_agent.observability.otel import span as otel_span
from troubleshooting_agent.prompts.system import SYSTEM_PROMPT


class AgentState(TypedDict):
    """Graph state: conversation messages."""

    messages: Annotated[list[BaseMessage], add_messages]


def _should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Route to tools node if the last message has tool calls."""
    messages = state["messages"]
    if not messages:
        return "__end__"
    last = messages[-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "__end__"


def build_agent_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
) -> StateGraph[AgentState, None, AgentState, AgentState]:
    """
    Build a LangGraph ReAct-style loop: agent -> tools -> agent -> ...

    Args:
        llm: Chat model (Ollama or Azure OpenAI)
        tools: LangChain tools to bind (may be empty)
    """
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
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
        invoke_model = model
        if model_force_tools is not None and not has_tool_results:
            invoke_model = model_force_tools
        with otel_span("agent.llm.turn"):
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
    graph.add_node("agent", call_model)

    if tool_node is not None:
        graph.add_node("tools", tool_node)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", "__end__": END})
        graph.add_edge("tools", "agent")
    else:
        graph.set_entry_point("agent")
        graph.add_edge("agent", END)

    return graph
