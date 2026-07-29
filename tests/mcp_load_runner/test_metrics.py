"""Tests for MCP load runner metrics."""

from mcp_load_runner.metrics import (
    ParticipantResult,
    RunConfigMetadata,
    ToolCallRecord,
    build_summary,
    classify_error,
    percentile,
    redact_secrets,
    slowest_tool_by_p95,
    suggest_next_participants,
)
import pytest

from mcp_load_runner.runner import MAX_PARTICIPANTS, LoadTestConfig


def test_percentile_interpolation() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 50) == 30.0
    assert percentile(values, 95) is not None


def test_classify_error_rate_limit() -> None:
    assert classify_error("HTTP 429 Too Many Requests") == "rate_limit"
    assert classify_error("request timed out") == "timeout"


def test_redact_secrets() -> None:
    text = redact_secrets("Authorization: Bearer sk-secret-token-123")
    assert "sk-secret" not in text
    assert "REDACTED" in text


def test_build_summary_aggregates() -> None:
    records = [
        ToolCallRecord(
            participant_id=1,
            step=1,
            tool_name="o11y_get_apm_services",
            server="splunk_o11y",
            started_at="2026-01-01T00:00:00+00:00",
            duration_ms=100.0,
            success=True,
            response_bytes=50,
        ),
        ToolCallRecord(
            participant_id=1,
            step=2,
            tool_name="splunk_run_query",
            server="splunk_cloud_mcp",
            started_at="2026-01-01T00:00:01+00:00",
            duration_ms=200.0,
            success=False,
            error_type="rate_limit",
            error_message="429 throttled",
        ),
    ]
    summary = build_summary(
        participants=1,
        ramp_up_seconds=0.0,
        wall_clock_ms=500.0,
        participant_results=[
            ParticipantResult(participant_id=1, success=False, duration_ms=500.0, records=records)
        ],
        records=records,
    )
    assert summary.total_calls == 2
    assert summary.failed_calls == 1
    assert summary.error_rate_pct == 50.0
    assert summary.errors_by_type.get("rate_limit") == 1
    assert "o11y_get_apm_services" in summary.latency_by_tool


def test_load_test_config_rejects_over_max() -> None:
    with pytest.raises(ValueError, match=str(MAX_PARTICIPANTS)):
        LoadTestConfig(participants=MAX_PARTICIPANTS + 1)


def test_load_test_config_allows_max() -> None:
    config = LoadTestConfig(participants=MAX_PARTICIPANTS)
    assert config.participants == MAX_PARTICIPANTS


def test_slowest_tool_by_p95() -> None:
    latency = {
        "fast_tool": {"p95_ms": 100.0},
        "slow_tool": {"p95_ms": 12000.0},
    }
    assert slowest_tool_by_p95(latency) == ("slow_tool", 12000.0)


def test_suggest_next_participants_after_clean_run() -> None:
    message = suggest_next_participants(
        participants=4,
        error_rate_pct=0.0,
        use_o11y=True,
        use_cloud=False,
    )
    assert "10" in message
    assert "mcp-remote" in message


def test_build_summary_includes_run_config() -> None:
    run_config = RunConfigMetadata(
        service_name="api",
        environment_name="prod",
        server_selection_label="Splunk O11y Cloud",
        use_o11y=True,
        use_cloud=False,
        ramp_up_seconds=30.0,
        call_timeout_seconds=60.0,
        stop_on_first_error=False,
        steps_per_participant=5,
        finished_at="2026-01-01T00:00:00+00:00",
    )
    summary = build_summary(
        participants=1,
        ramp_up_seconds=30.0,
        wall_clock_ms=1000.0,
        participant_results=[
            ParticipantResult(participant_id=1, success=True, duration_ms=1000.0)
        ],
        records=[],
        run_config=run_config,
    )
    assert summary.run_config is not None
    assert summary.run_config.service_name == "api"
    assert "run_config" in summary.to_dict()
