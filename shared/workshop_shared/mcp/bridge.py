"""Convert MCP tools to LangChain tools and format results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, Tool
from pydantic import BaseModel, Field, create_model

from workshop_shared.config import Settings
from workshop_shared.mcp.connect import connect_mcp_session
from workshop_shared.mcp.gateway import (
    splunk_cloud_mcp_params,
    splunk_enterprise_mcp_params,
    splunk_o11y_gateway_params,
)
from workshop_shared.observability.logging_trace import log_mcp_call
from workshop_shared.observability.otel import span as otel_span

# ---------------------------------------------------------------------------
# Health-check result type
# Returned by mcp-doctor; no secrets in tool lists or errors.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class McpServerInfo:
    """Result of an MCP connectivity check."""

    name: str
    ok: bool
    tool_count: int
    tool_names: list[str]
    error: str | None = None


# ---------------------------------------------------------------------------
# Schema → Pydantic
# MCP tools declare JSON Schema; we build a Pydantic model for LangChain args.
# ---------------------------------------------------------------------------


def _json_schema_to_model(tool_name: str, schema: dict[str, Any] | None) -> type[BaseModel]:
    """Build a Pydantic model from an MCP JSON Schema object."""
    if not schema or schema.get("type") != "object":
        return create_model(f"{tool_name}_args")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return create_model(f"{tool_name}_args")

    fields: dict[str, Any] = {}
    for key, prop in properties.items():
        if not isinstance(prop, dict):
            if key == "params":
                fields[key] = (dict[str, Any], Field(default_factory=dict))
            else:
                fields[key] = (Any, None)
            continue
        description = prop.get("description")
        # MCP marks ``params`` required, but models often send {} or flat kwargs.
        # Default empty params so ToolNode can invoke and _normalize_mcp_arguments can wrap.
        if key == "params":
            fields[key] = (
                dict[str, Any],
                Field(default_factory=dict, description=description),
            )
        else:
            fields[key] = (
                (Any, Field(default=None, description=description)) if description else (Any, None)
            )

    return create_model(f"{tool_name}_args", **fields)


# ---------------------------------------------------------------------------
# Argument normalization
# o11y MCP tools require {"params": {...}}; models often send flat kwargs.
# ---------------------------------------------------------------------------


def normalize_tool_call_args(schema: dict[str, Any] | None, args: dict[str, Any]) -> dict[str, Any]:
    """Normalize LangChain tool-call args before ToolNode / MCP invocation."""
    return _normalize_mcp_arguments(schema, args)


def _coerce_time_range(value: Any) -> Any:
    """O11y MCP tools expect time_range as {start, stop}; models often send a duration string."""
    if isinstance(value, str) and value.strip():
        return {"start": value.strip(), "stop": "now"}
    return value


def _coerce_o11y_params(params: dict[str, Any]) -> dict[str, Any]:
    """Fix common LLM argument shapes before MCP invocation."""
    if not params:
        return params
    coerced = dict(params)
    if "time_range" in coerced:
        coerced["time_range"] = _coerce_time_range(coerced["time_range"])
    return coerced


def _finalize_mcp_arguments(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Always wrap params and coerce O11y-specific argument shapes."""
    if not kwargs:
        return {"params": {}}
    if "params" in kwargs and isinstance(kwargs["params"], dict):
        return {**kwargs, "params": _coerce_o11y_params(kwargs["params"])}
    if "params" not in kwargs:
        return {"params": _coerce_o11y_params(kwargs)}
    return kwargs


def _normalize_mcp_arguments(
    schema: dict[str, Any] | None,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """
    MCP o11y tools require a top-level ``params`` object.

    Models often send flat kwargs or ``{}``; wrap when needed.
    """
    if not schema or schema.get("type") != "object":
        return _finalize_mcp_arguments(kwargs)

    properties = schema.get("properties", {})
    if "params" not in properties:
        return _finalize_mcp_arguments(kwargs)

    if "params" in kwargs:
        return _finalize_mcp_arguments(kwargs)

    # Empty tool call -> {"params": {}}
    if not kwargs:
        return {"params": {}}

    return _finalize_mcp_arguments(kwargs)


# ---------------------------------------------------------------------------
# MCP result formatting
# Turn CallToolResult into a string the LLM can read in the next turn.
# ---------------------------------------------------------------------------

# Large APM payloads can exceed the LLM context window; cap tool output size.
_MCP_RESULT_MAX_CHARS = 32_000


def _truncate_for_llm(text: str, *, max_chars: int = _MCP_RESULT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars + 200
    return (
        text[: max_chars - 200]
        + f"\n\n... [truncated ~{omitted} chars — narrow time range or filters and retry]"
    )


def _format_call_tool_result(result: CallToolResult) -> str:
    """Serialize MCP tool output for the LLM."""
    parts: list[str] = []
    if result.isError:
        parts.append("ERROR:")
    for block in result.content:
        if isinstance(block, TextContent):
            parts.append(block.text)
        else:
            parts.append(str(block))
    if not parts and result.structuredContent is not None:
        parts.append(json.dumps(result.structuredContent, indent=2, default=str))
    formatted = "\n".join(parts) if parts else "(empty tool result)"
    return _truncate_for_llm(formatted)


# ---------------------------------------------------------------------------
# LangChain tool wrapper
# Each MCP tool becomes an async StructuredTool that calls session.call_tool.
# ---------------------------------------------------------------------------


def _wrap_mcp_tool(session: ClientSession, mcp_tool: Tool) -> StructuredTool:
    schema = mcp_tool.inputSchema if isinstance(mcp_tool.inputSchema, dict) else None
    args_model = _json_schema_to_model(mcp_tool.name, schema)

    async def _arun(**kwargs: Any) -> str:
        clean = {k: v for k, v in kwargs.items() if v is not None}
        arguments = _normalize_mcp_arguments(schema, clean)
        with otel_span(
            "mcp.tool",
            {"mcp.tool.name": mcp_tool.name},
        ):
            result = await session.call_tool(mcp_tool.name, arguments=arguments)
            formatted = _format_call_tool_result(result)
        log_mcp_call(tool_name=mcp_tool.name, arguments=arguments, result=formatted)
        return formatted

    return StructuredTool.from_function(
        coroutine=_arun,
        name=mcp_tool.name,
        description=mcp_tool.description or mcp_tool.name,
        args_schema=args_model,
        metadata={"mcp_input_schema": schema},
    )


async def create_langchain_tools_from_session(
    session: ClientSession,
    *,
    name_prefix: str | None = None,
) -> list[BaseTool]:
    """Wrap MCP session tools as async LangChain StructuredTools."""
    listed = await session.list_tools()
    tools: list[BaseTool] = []
    for mcp_tool in listed.tools:
        if name_prefix and not mcp_tool.name.startswith(name_prefix):
            continue
        tools.append(_wrap_mcp_tool(session, mcp_tool))
    return tools


# ---------------------------------------------------------------------------
# MCP connectivity probes
# Used by mcp-doctor to verify each enabled Splunk MCP server.
# ---------------------------------------------------------------------------


async def check_mcp_servers(settings: Settings) -> list[McpServerInfo]:
    """Probe configured MCP servers and return tool lists (no secrets in output)."""
    results: list[McpServerInfo] = []

    if settings.enable_splunk_o11y:
        results.append(
            await _check_server(
                "splunk_o11y",
                splunk_o11y_gateway_params(settings),
                settings.splunk_o11y_tool_prefix,
            )
        )

    if settings.enable_splunk_cloud_mcp:
        results.append(
            await _check_server(
                "splunk_cloud_mcp",
                splunk_cloud_mcp_params(settings),
                None,
            )
        )

    if settings.enable_splunk_mcp:
        results.append(
            await _check_server(
                "splunk_enterprise_mcp",
                splunk_enterprise_mcp_params(settings),
                None,
            )
        )

    return results


async def _check_server(
    name: str,
    params: Any,
    name_prefix: str | None,
) -> McpServerInfo:
    try:
        async with connect_mcp_session(params) as session:
            listed = await session.list_tools()
            names = [
                t.name for t in listed.tools if not name_prefix or t.name.startswith(name_prefix)
            ]
            return McpServerInfo(name=name, ok=True, tool_count=len(names), tool_names=names)
    except Exception as exc:
        return McpServerInfo(name=name, ok=False, tool_count=0, tool_names=[], error=str(exc))
