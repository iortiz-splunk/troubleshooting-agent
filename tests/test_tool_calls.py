"""Tests for Ollama text tool-call parsing."""

from langchain_core.messages import AIMessage

from troubleshooting_agent.agent.tool_calls import (
    ensure_ai_tool_calls,
    extract_tool_calls_from_text,
)


def test_extract_tool_calls_from_json_text() -> None:
    text = '{"name": "o11y_get_apm_environments", "arguments": {}}'
    calls = extract_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "o11y_get_apm_environments"
    assert calls[0]["args"] == {}


def test_ensure_ai_tool_calls_wraps_flat_args_in_params() -> None:
    message = AIMessage(
        content='{"name": "o11y_search_alerts_or_incidents", "arguments": {"service_name": "api"}}'
    )
    schema = {
        "type": "object",
        "properties": {"params": {"type": "object"}},
        "required": ["params"],
    }
    tool = type("T", (), {"metadata": {"mcp_input_schema": schema}})()
    updated = ensure_ai_tool_calls(
        message,
        tools_by_name={"o11y_search_alerts_or_incidents": tool},
    )
    assert updated.tool_calls[0]["args"] == {"params": {"service_name": "api"}}


def test_ensure_ai_tool_calls_populates_tool_calls() -> None:
    message = AIMessage(content='{"name": "o11y_search_alerts_or_incidents", "arguments": {}}')
    schema = {
        "type": "object",
        "properties": {"params": {"type": "object"}},
        "required": ["params"],
    }
    tool = type("T", (), {"metadata": {"mcp_input_schema": schema}})()
    updated = ensure_ai_tool_calls(
        message,
        tools_by_name={"o11y_search_alerts_or_incidents": tool},
    )
    assert updated.tool_calls
    assert updated.tool_calls[0]["args"] == {"params": {}}
