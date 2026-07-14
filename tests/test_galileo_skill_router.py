"""Tests for Galileo skill router instrumentation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workshop_shared.observability.galileo import log_skill_router_to_galileo


@dataclass
class _FakeGalileoLogger:
    traces: list[dict[str, Any]] = field(default_factory=list)
    workflow_spans: list[dict[str, Any]] = field(default_factory=list)
    concluded: list[dict[str, Any]] = field(default_factory=list)
    flush_count: int = 0

    def start_trace(self, **kwargs: Any) -> None:
        self.traces.append(kwargs)

    def add_workflow_span(self, **kwargs: Any) -> None:
        self.workflow_spans.append(kwargs)

    def conclude(self, **kwargs: Any) -> None:
        self.concluded.append(kwargs)

    def flush(self) -> list[Any]:
        self.flush_count += 1
        return []


def test_log_skill_router_emits_trace_and_spans() -> None:
    logger = _FakeGalileoLogger()
    metadata = {
        "workshop_part": "part2_agent",
        "skill_router": "keyword",
        "skill": "latency-spike",
        "skills": "latency-spike,investigation-report",
        "skill_routing": (
            '{"router":"keyword","domain_skill":"latency-spike",'
            '"loaded_skills":["latency-spike","investigation-report"],'
            '"scores":{"latency-spike":2,"alert-triage":0},'
            '"chars_by_skill":{"latency-spike":1200,"investigation-report":800},'
            '"haystack_preview":"investigate latency spike"}'
        ),
    }

    log_skill_router_to_galileo(logger, investigation_metadata=metadata)

    assert len(logger.traces) == 1
    assert logger.traces[0]["name"] == "skill_router"
    assert "latency-spike" in logger.traces[0]["input"]
    assert len(logger.workflow_spans) == 2
    assert logger.workflow_spans[0]["name"] == "load_skill:latency-spike"
    assert logger.workflow_spans[1]["name"] == "load_skill:investigation-report"
    assert logger.concluded[0]["status_code"] == 200
    assert logger.flush_count == 1


def test_log_skill_router_skips_without_skills() -> None:
    logger = _FakeGalileoLogger()
    log_skill_router_to_galileo(logger, investigation_metadata={"workshop_part": "part1_agent"})
    assert logger.traces == []
    assert logger.workflow_spans == []


def test_log_skill_router_part3_graph_entry() -> None:
    logger = _FakeGalileoLogger()
    metadata = {
        "workshop_part": "part3_agent",
        "skill_router": "graph_entry",
        "skill": "troubleshoot",
        "skills": "troubleshoot",
        "skill_routing": (
            '{"router":"graph_entry","domain_skill":"troubleshoot",'
            '"loaded_skills":["troubleshoot"],"scores":{},'
            '"chars_by_skill":{"troubleshoot":2400},"haystack_preview":""}'
        ),
    }

    log_skill_router_to_galileo(logger, investigation_metadata=metadata)

    assert len(logger.traces) == 1
    assert logger.traces[0]["name"] == "skill_router"
    assert "graph_entry" in logger.traces[0]["input"]
    assert logger.workflow_spans[0]["name"] == "load_skill:troubleshoot"

