"""Convert MCP tools to LangChain tools and format results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from mcp import ClientSession
from mcp.types import CallToolResult, TextContent, Tool
from pydantic import BaseModel, Field, create_model

from troubleshooting_agent.config import Settings
from troubleshooting_agent.mcp.connect import connect_mcp_session
from troubleshooting_agent.mcp.gateway import (
    splunk_cloud_mcp_params,
    splunk_enterprise_mcp_params,
    splunk_o11y_gateway_params,
)


@dataclass(frozen=True)
class McpServerInfo:
    """Result of an MCP connectivity check."""

    name: str
    ok: bool
    tool_count: int
    tool_names: list[str]
    error: str | None = None


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
            fields[key] = (dict[str, Any], Field(default_factory=dict)) if key == "params" else (Any, None)
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
                (Any, Field(default=None, description=description))
                if description
                else (Any, None)
            )

    return create_model(f"{tool_name}_args", **fields)


def normalize_tool_call_args(schema: dict[str, Any] | None, args: dict[str, Any]) -> dict[str, Any]:
    """Normalize LangChain tool-call args before ToolNode / MCP invocation."""
    return _normalize_mcp_arguments(schema, args)


def _normalize_mcp_arguments(schema: dict[str, Any] | None, kwargs: dict[str, Any]) -> dict[str, Any]:
    """
    MCP o11y tools require a top-level ``params`` object.

    Models often send flat kwargs or ``{}``; wrap when needed.
    """
    if not schema or schema.get("type") != "object":
        return kwargs

    properties = schema.get("properties", {})
    if "params" not in properties:
        return kwargs

    if "params" in kwargs:
        return kwargs

    # Empty tool call -> {"params": {}}
    if not kwargs:
        return {"params": {}}

    return {"params": kwargs}


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
    return "\n".join(parts) if parts else "(empty tool result)"


def _wrap_mcp_tool(session: ClientSession, mcp_tool: Tool) -> StructuredTool:
    schema = mcp_tool.inputSchema if isinstance(mcp_tool.inputSchema, dict) else None
    args_model = _json_schema_to_model(mcp_tool.name, schema)

    async def _arun(**kwargs: Any) -> str:
        clean = {k: v for k, v in kwargs.items() if v is not None}
        arguments = _normalize_mcp_arguments(schema, clean)
        result = await session.call_tool(mcp_tool.name, arguments=arguments)
        return _format_call_tool_result(result)

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


async def check_mcp_servers(settings: Settings) -> list[McpServerInfo]:
    """Probe configured MCP servers and return tool lists (no secrets in output)."""
    results: list[McpServerInfo] = []

    if settings.enable_splunk_o11y:
        results.append(await _check_server(
            "splunk_o11y",
            splunk_o11y_gateway_params(settings),
            settings.splunk_o11y_tool_prefix,
        ))

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
                t.name
                for t in listed.tools
                if not name_prefix or t.name.startswith(name_prefix)
            ]
            return McpServerInfo(name=name, ok=True, tool_count=len(names), tool_names=names)
    except Exception as exc:
        return McpServerInfo(name=name, ok=False, tool_count=0, tool_names=[], error=str(exc))
