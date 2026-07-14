"""Tests for per-investigation JSONL trace files."""

from __future__ import annotations

import json
from pathlib import Path

from workshop_shared.config import Settings
from workshop_shared.observability.investigation_log import (
    alert_identifiers,
    close_investigation_log,
    open_investigation_log,
    summarize_mcp_alerts,
    write_investigation_log,
)
from workshop_shared.observability.logging_trace import (
    investigation_scope,
    log_mcp_call,
    log_node_snapshot,
)


def test_alert_identifiers_extracts_o11y_fields() -> None:
    ids = alert_identifiers(
        {
            "eventId": "HNIDYnrAwAA",
            "incidentId": "CHkAbC123",
            "detectorId": "det-999",
            "detectLabel": "latency-high",
            "customProperties": {"sf_service": "Verification", "sf_environment": "prod"},
        }
    )
    assert ids["event_id"] == "HNIDYnrAwAA"
    assert ids["incident_id"] == "CHkAbC123"
    assert ids["detector_id"] == "det-999"
    assert ids["sf_service"] == "Verification"


def test_summarize_mcp_alerts_parses_search_results() -> None:
    payload = {
        "alerts": [
            {"eventId": "A1", "detectorId": "d1"},
            {"eventId": "A2", "detectorId": "d2"},
        ]
    }
    rows = summarize_mcp_alerts(json.dumps(payload))
    assert len(rows) == 2
    assert rows[0]["event_id"] == "A1"


def test_investigation_scope_writes_jsonl_file(tmp_path: Path) -> None:
    settings = Settings(agent_log_dir=str(tmp_path), agent_log_trace=False)
    with investigation_scope(
        settings,
        "slack:1783966776.556919",
        metadata={"event_id": "HNIDYnrAwAA", "service": "Verification"},
    ):
        write_investigation_log("custom_event", note="hello")
        log_node_snapshot(
            node="investigate",
            phase="enter",
            investigation_metadata={"event_id": "HNIDYnrAwAA"},
            alert_payload={"eventId": "HNIDYnrAwAA", "detectorId": "det-1"},
        )
        log_mcp_call(
            tool_name="o11y_search_alerts_or_incidents",
            arguments={"params": {"service_name": "Verification"}},
            result=json.dumps(
                {"alerts": [{"eventId": "OTHER", "detectorId": "det-other"}]}
            ),
        )

    log_file = tmp_path / "slack-1783966776.556919.jsonl"
    assert log_file.is_file()
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    events = [line["event"] for line in lines]
    assert "investigation_start" in events
    assert "node_snapshot" in events
    assert "mcp_call" in events
    assert "investigation_done" in events

    snapshot = next(line for line in lines if line["event"] == "node_snapshot")
    assert snapshot["alert"]["event_id"] == "HNIDYnrAwAA"

    mcp_line = next(line for line in lines if line["event"] == "mcp_call")
    assert mcp_line["alerts_returned"][0]["event_id"] == "OTHER"


def test_open_and_close_without_dir_setting() -> None:
    settings = Settings(agent_log_dir="")
    assert open_investigation_log(settings, "chat:abc") is None
    close_investigation_log()
