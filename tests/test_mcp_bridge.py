"""Tests for MCP bridge (mocked session)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import ListToolsResult, TextContent, Tool

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import (
    _format_call_tool_result,
    _normalize_mcp_arguments,
    check_mcp_servers,
    create_langchain_tools_from_session,
    normalize_tool_call_args,
)


def test_format_call_tool_result() -> None:
    result = MagicMock()
    result.isError = False
    result.content = [TextContent(type="text", text="ok")]
    result.structuredContent = None
    assert _format_call_tool_result(result) == "ok"


def test_format_call_tool_result_truncates_large_payload() -> None:
    from workshop_shared.mcp.bridge import _MCP_RESULT_MAX_CHARS

    result = MagicMock()
    result.isError = False
    result.content = [TextContent(type="text", text="x" * (_MCP_RESULT_MAX_CHARS + 5000))]
    result.structuredContent = None
    formatted = _format_call_tool_result(result)
    assert len(formatted) < _MCP_RESULT_MAX_CHARS + 500
    assert "truncated" in formatted


def test_normalize_tool_call_args_alias() -> None:
    schema = {
        "type": "object",
        "properties": {"params": {"type": "object"}},
        "required": ["params"],
    }
    assert normalize_tool_call_args(schema, {"service_name": "api"}) == {
        "params": {"service_name": "api"}
    }


def test_normalize_mcp_arguments_wraps_params() -> None:
    schema = {
        "type": "object",
        "properties": {"params": {"type": "object"}},
        "required": ["params"],
    }
    assert _normalize_mcp_arguments(schema, {}) == {"params": {}}
    assert _normalize_mcp_arguments(schema, {"service_name": "api"}) == {
        "params": {"service_name": "api"}
    }


def test_normalize_mcp_arguments_coerces_time_range_string() -> None:
    schema = {
        "type": "object",
        "properties": {"params": {"type": "object"}},
        "required": ["params"],
    }
    assert _normalize_mcp_arguments(
        schema,
        {"params": {"service_name": "api", "time_range": "-1h"}},
    ) == {
        "params": {"service_name": "api", "time_range": {"start": "-1h", "stop": "now"}},
    }
    assert _normalize_mcp_arguments(
        schema,
        {"service_name": "api", "time_range": "-30m"},
    ) == {
        "params": {"service_name": "api", "time_range": {"start": "-30m", "stop": "now"}},
    }
    # Coercion still applies when schema is missing (e.g. tool_calls repair path).
    assert _normalize_mcp_arguments(
        None,
        {"params": {"service_name": "api", "time_range": "-1h"}},
    ) == {
        "params": {"service_name": "api", "time_range": {"start": "-1h", "stop": "now"}},
    }


@pytest.mark.asyncio
async def test_create_langchain_tools_from_session() -> None:
    session = AsyncMock()
    session.list_tools.return_value = ListToolsResult(
        tools=[
            Tool(
                name="o11y_search_alerts",
                description="Search alerts",
                inputSchema={"type": "object"},
            ),
            Tool(name="other_tool", description="Other", inputSchema={"type": "object"}),
        ]
    )
    session.call_tool.return_value = MagicMock(
        isError=False,
        content=[TextContent(type="text", text="[]")],
        structuredContent=None,
    )

    tools = await create_langchain_tools_from_session(session, name_prefix="o11y_")
    assert len(tools) == 1
    assert tools[0].name == "o11y_search_alerts"


@pytest.mark.asyncio
async def test_check_mcp_servers_disabled() -> None:
    settings = Settings(enable_splunk_o11y=False, enable_splunk_mcp=False)
    results = await check_mcp_servers(settings)
    assert results == []
