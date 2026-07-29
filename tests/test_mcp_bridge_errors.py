"""Tests for MCP bridge error formatting."""

from workshop_shared.mcp.bridge import _format_mcp_error


def test_format_mcp_error_unwraps_exception_group() -> None:
    inner = ValueError("self signed certificate in certificate chain")
    group = ExceptionGroup("unhandled errors in a TaskGroup", [inner])
    message = _format_mcp_error(group)
    assert "self signed certificate" in message.lower()
    assert "MCP_TLS_INSECURE" in message


def test_format_mcp_error_plain_exception() -> None:
    assert _format_mcp_error(RuntimeError("connection refused")) == "connection refused"
