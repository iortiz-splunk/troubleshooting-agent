"""Tests for Galileo session token tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workshop_shared.observability.galileo import (
    TokenUsageTotals,
    _make_token_ingestion_hook,
    _prepare_session_metadata,
    finalize_galileo_session_tokens,
    GalileoSession,
)


@dataclass
class _FakeTrace:
    user_metadata: dict[str, str] | None = None


@dataclass
class _FakeIngestRequest:
    traces: list[_FakeTrace]


@dataclass
class _FakeGalileoLogger:
    traces: list[dict[str, Any]] = field(default_factory=list)
    concluded: list[dict[str, Any]] = field(default_factory=list)
    flush_count: int = 0
    ingested: list[Any] = field(default_factory=list)

    def start_trace(self, **kwargs: Any) -> None:
        self.traces.append(kwargs)

    def conclude(self, **kwargs: Any) -> None:
        self.concluded.append(kwargs)

    def flush(self) -> list[Any]:
        self.flush_count += 1
        return []

    def ingest_traces(self, ingest_request: Any) -> None:
        self.ingested.append(ingest_request)


def test_token_usage_totals_accumulates() -> None:
    totals = TokenUsageTotals()
    totals.add(input_tokens=100, output_tokens=20, total_tokens=120)
    totals.add(input_tokens=50, output_tokens=10, total_tokens=60)

    assert totals.llm_calls == 2
    assert totals.input_tokens == 150
    assert totals.output_tokens == 30
    assert totals.total_tokens == 180

    meta = totals.to_session_metadata()
    assert meta["input_tokens"] == "150"
    assert meta["output_tokens"] == "30"
    assert meta["total_tokens"] == "180"
    assert meta["llm_calls"] == "2"


def test_prepare_session_metadata_adds_token_placeholders() -> None:
    meta = _prepare_session_metadata({"workshop_part": "part3_agent"})
    assert meta["workshop_part"] == "part3_agent"
    assert meta["input_tokens"] == "0"
    assert meta["output_tokens"] == "0"
    assert meta["total_tokens"] == "0"
    assert meta["llm_calls"] == "0"


def test_token_ingestion_hook_stamps_metadata_and_ingests() -> None:
    logger = _FakeGalileoLogger()
    totals = TokenUsageTotals()
    totals.add(input_tokens=10, output_tokens=5, total_tokens=15)
    trace = _FakeTrace()
    request = _FakeIngestRequest(traces=[trace])

    hook = _make_token_ingestion_hook(logger, totals)
    hook(request)

    assert trace.user_metadata == {
        "input_tokens": "10",
        "output_tokens": "5",
        "total_tokens": "15",
        "llm_calls": "1",
    }
    assert logger.ingested == [request]


@dataclass
class _FakeGalileoLoggerForFinalize:
    traces: list[dict[str, Any]] = field(default_factory=list)
    concluded: list[dict[str, Any]] = field(default_factory=list)
    flush_count: int = 0

    def start_trace(self, **kwargs: Any) -> None:
        self.traces.append(kwargs)

    def conclude(self, **kwargs: Any) -> None:
        self.concluded.append(kwargs)

    def flush(self) -> list[Any]:
        self.flush_count += 1
        return []


def test_finalize_galileo_session_tokens_logs_session_usage() -> None:
    totals = TokenUsageTotals()
    totals.add(input_tokens=1000, output_tokens=250, total_tokens=1250)
    session = GalileoSession(
        callback=object(),
        logger=_FakeGalileoLoggerForFinalize(),
        token_totals=totals,
    )

    finalize_galileo_session_tokens(session)

    logger = session.logger
    assert len(logger.traces) == 1
    assert logger.traces[0]["name"] == "session_usage"
    assert logger.traces[0]["metadata"]["total_tokens"] == "1250"
    assert logger.flush_count == 1


def test_finalize_skips_when_no_llm_calls() -> None:
    session = GalileoSession(
        callback=object(),
        logger=_FakeGalileoLoggerForFinalize(),
        token_totals=TokenUsageTotals(),
    )
    finalize_galileo_session_tokens(session)
    assert session.logger.traces == []
