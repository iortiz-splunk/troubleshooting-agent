"""Invoke the troubleshooting agent and format output."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from troubleshooting_agent.agent.graph import build_agent_graph
from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.ollama import build_llm
from troubleshooting_agent.tools.base import get_tools


def run_chat(settings: Settings, user_message: str) -> str:
    """
    Run the agent graph with a single user message and return the final reply.

    Args:
        settings: Application settings
        user_message: User's troubleshooting question

    Returns:
        Final assistant text response
    """
    llm = build_llm(settings)
    tools = get_tools(settings)
    graph = build_agent_graph(llm, tools)
    app = graph.compile()

    result = app.invoke({"messages": [HumanMessage(content=user_message)]})
    messages = result.get("messages", [])

    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
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

    return "No response generated."
