"""Helpers when models emit tool calls as JSON text instead of structured tool_calls."""

from __future__ import annotations

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

from troubleshooting_agent.mcp.bridge import normalize_tool_call_args


def extract_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    """
    Parse tool call JSON blobs from model text output.

    Ollama models often print {"name": "...", "arguments": {...}} instead of
    populating AIMessage.tool_calls.
    """
    tool_calls: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx += 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("name"), str):
            args = obj.get("arguments")
            if args is None:
                args = obj.get("args")
            if not isinstance(args, dict):
                args = {}
            tool_calls.append(
                {
                    "name": obj["name"],
                    "args": args,
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                }
            )
        idx = max(end, idx + 1)
    return tool_calls


def _normalize_calls(
    tool_calls: list[dict[str, Any]],
    tools_by_name: dict[str, BaseTool],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("args")
        if not isinstance(args, dict):
            args = {}
        tool = tools_by_name.get(name) if isinstance(name, str) else None
        schema = None
        if tool is not None and tool.metadata:
            schema = tool.metadata.get("mcp_input_schema")
        normalized.append(
            {
                **call,
                "args": normalize_tool_call_args(schema, args),
            }
        )
    return normalized


def ensure_ai_tool_calls(
    message: AIMessage,
    *,
    tools_by_name: dict[str, BaseTool] | None = None,
) -> AIMessage:
    """Copy parsed tool calls onto the AIMessage when the model only wrote JSON text."""
    tools_by_name = tools_by_name or {}
    if message.tool_calls:
        calls = _normalize_calls(list(message.tool_calls), tools_by_name)
        if calls != list(message.tool_calls):
            return AIMessage(
                content=message.content,
                tool_calls=calls,
                additional_kwargs=message.additional_kwargs,
                response_metadata=message.response_metadata,
            )
        return message
    content = message.content
    if not isinstance(content, str) or not content.strip():
        return message
    parsed = extract_tool_calls_from_text(content)
    if not parsed:
        return message
    calls = _normalize_calls(parsed, tools_by_name)
    return AIMessage(
        content="",
        tool_calls=calls,
        additional_kwargs=message.additional_kwargs,
        response_metadata=message.response_metadata,
    )
