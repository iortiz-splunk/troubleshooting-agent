"""Tests for agent logging trace helpers."""

from __future__ import annotations

import logging

import pytest

from workshop_shared.config import Settings
from workshop_shared.observability.logging_trace import (
    investigation_scope,
    log_agent_response,
    log_investigation_banner,
    log_mcp_call,
    preview,
    preview_params,
)


def test_preview_truncates() -> None:
    text = "a" * 200
    assert preview(text, limit=50).endswith("...")
    assert len(preview(text, limit=50)) == 50


def test_preview_params_redacts_secrets() -> None:
    raw = preview_params({"params": {"api_key": "secret-value", "service_name": "api"}})
    assert "secret-value" not in raw
    assert "<redacted>" in raw
    assert "api" in raw


def test_investigation_scope_correlates_logs(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(agent_log_trace=True)
    caplog.set_level(logging.INFO, logger="workshop_shared")

    with investigation_scope(settings, "slack:1234.5678", metadata={"service": "Verification"}):
        log_mcp_call(
            tool_name="o11y_search_alerts",
            arguments={"params": {"service_name": "Verification"}},
            result="[]",
        )

    assert any("[inv=slack:1234.5678]" in r.message for r in caplog.records)
    assert any("MCP o11y_search_alerts — OK" in r.message for r in caplog.records)


def test_log_mcp_call_error_line(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(agent_log_trace=True)
    caplog.set_level(logging.INFO, logger="workshop_shared")

    with investigation_scope(settings, "chat:abc"):
        log_mcp_call(
            tool_name="o11y_get_metrics",
            arguments={"params": {}},
            result="ERROR:\ninvalid environment_name",
        )

    assert any("MCP o11y_get_metrics — ERROR" in r.message for r in caplog.records)


def test_log_investigation_banner(caplog: pytest.LogCaptureFixture, tmp_path) -> None:
    settings = Settings(agent_log_trace=True, agent_log_dir=str(tmp_path))
    caplog.set_level(logging.INFO, logger="workshop_shared")

    with investigation_scope(settings, "chat:banner1"):
        log_investigation_banner(
            workshop_part="part2",
            source="cli",
            query="Investigate latency on Verification",
            provider="ollama",
            mcp_tool_count=8,
            skill="latency-spike",
        )

    messages = " ".join(r.message for r in caplog.records)
    assert "part2" in messages
    assert "latency-spike" in messages
    assert "Investigate latency on Verification" in messages


def test_log_agent_response(caplog: pytest.LogCaptureFixture, tmp_path) -> None:
    settings = Settings(agent_log_trace=True, agent_log_dir=str(tmp_path))
    caplog.set_level(logging.INFO, logger="workshop_shared")

    with investigation_scope(settings, "chat:resp1"):
        log_agent_response("- Finding one\n- Finding two")

    messages = " ".join(r.message for r in caplog.records)
    assert "Agent response" in messages
    assert "Finding one" in messages

    log_file = tmp_path / "chat-resp1.jsonl"
    assert log_file.is_file()
    assert "agent_response" in log_file.read_text(encoding="utf-8")
