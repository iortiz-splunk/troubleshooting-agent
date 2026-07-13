"""Tests for agent logging trace helpers."""

from __future__ import annotations

import logging

import pytest

from troubleshooting_agent.config import Settings
from troubleshooting_agent.observability.logging_trace import (
    investigation_scope,
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
    caplog.set_level(logging.INFO, logger="troubleshooting_agent")

    with investigation_scope(settings, "slack:1234.5678", metadata={"service": "Verification"}):
        log_mcp_call(
            tool_name="o11y_search_alerts",
            arguments={"params": {"service_name": "Verification"}},
            result="[]",
        )

    assert any("[inv=slack:1234.5678]" in r.message for r in caplog.records)
    assert any("mcp o11y_search_alerts ok" in r.message for r in caplog.records)


def test_log_mcp_call_error_line(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(agent_log_trace=True)
    caplog.set_level(logging.INFO, logger="troubleshooting_agent")

    with investigation_scope(settings, "chat:abc"):
        log_mcp_call(
            tool_name="o11y_get_metrics",
            arguments={"params": {}},
            result="ERROR:\ninvalid environment_name",
        )

    assert any("mcp o11y_get_metrics ERROR" in r.message for r in caplog.records)
