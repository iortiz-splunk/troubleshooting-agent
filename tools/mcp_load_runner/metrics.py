"""Metrics collection and aggregation for MCP load tests."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

def redact_secrets(text: str) -> str:
    """Remove likely secrets from error messages before display or export."""
    redacted = text
    redacted = re.sub(r"(?i)bearer\s+\S+", "Bearer ***REDACTED***", redacted)
    redacted = re.sub(r"(?i)(token\s*[:=]\s*)\S+", r"\1***REDACTED***", redacted)
    redacted = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)\S+", r"\1***REDACTED***", redacted)
    redacted = re.sub(r"xox[bap]-[A-Za-z0-9-]+", "***REDACTED***", redacted)
    return redacted


def truncate_message(text: str, *, max_len: int = 500) -> str:
    cleaned = redact_secrets(text.strip())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def classify_error(error_message: str) -> str:
    """Heuristic error classification for capacity analysis."""
    lower = error_message.lower()
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "429" in lower or "rate limit" in lower or "throttl" in lower:
        return "rate_limit"
    if any(token in lower for token in ("401", "403", "unauthorized", "forbidden", "invalid token")):
        return "auth"
    if any(token in lower for token in ("validation", "invalid argument", "schema")):
        return "validation"
    if any(token in lower for token in ("500", "502", "503", "504", "internal server")):
        return "server_error"
    if "not found" in lower and "tool" in lower:
        return "tool_not_found"
    return "unknown"


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


@dataclass(frozen=True)
class ToolCallRecord:
    participant_id: int
    step: int
    tool_name: str
    server: str
    started_at: str
    duration_ms: float
    success: bool
    error_type: str | None = None
    error_message: str | None = None
    response_bytes: int = 0
    splunk_total_rows: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParticipantResult:
    participant_id: int
    success: bool
    duration_ms: float
    records: list[ToolCallRecord] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class RunProgress:
    total_participants: int
    completed: int = 0
    failed: int = 0
    in_flight: int = 0


@dataclass(frozen=True)
class RunConfigMetadata:
    """Run parameters stored with results for comparison and export."""

    service_name: str
    splunk_log_service: str
    environment_name: str
    server_selection_label: str
    use_o11y: bool
    use_cloud: bool
    ramp_up_seconds: float
    call_timeout_seconds: float
    stop_on_first_error: bool
    steps_per_participant: int
    include_exemplar_traces: bool
    exemplar_type: str
    finished_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunSummary:
    participants: int
    ramp_up_seconds: float
    wall_clock_ms: float
    total_calls: int
    successful_calls: int
    failed_calls: int
    error_rate_pct: float
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    latency_p99_ms: float | None
    calls_per_second: float
    participants_per_second: float
    slowest_participant_id: int | None
    slowest_participant_ms: float | None
    first_failure_at: str | None
    latency_by_tool: dict[str, dict[str, float | None]]
    errors_by_type: dict[str, int]
    server_breakdown: dict[str, dict[str, int | float]]
    records: list[ToolCallRecord] = field(default_factory=list)
    run_config: RunConfigMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["records"] = [record.to_dict() for record in self.records]
        if self.run_config is not None:
            payload["run_config"] = self.run_config.to_dict()
        return payload


def parse_splunk_total_rows(response_text: str) -> int | None:
    """Extract total_rows from a splunk_run_query JSON response."""
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    total_rows = payload.get("total_rows")
    if isinstance(total_rows, int):
        return total_rows
    if isinstance(total_rows, str) and total_rows.isdigit():
        return int(total_rows)
    return None


def splunk_zero_row_summary(records: list[ToolCallRecord]) -> str | None:
    """Return a warning when every parsed splunk_run_query call returned zero rows."""
    splunk_ok = [
        record
        for record in records
        if record.tool_name == "splunk_run_query" and record.success
    ]
    if not splunk_ok:
        return None
    parsed = [record for record in splunk_ok if record.splunk_total_rows is not None]
    if not parsed or not all(record.splunk_total_rows == 0 for record in parsed):
        return None
    return (
        f"All {len(parsed)} splunk_run_query call(s) returned 0 rows. "
        "Splunk latency may look artificially low — use a service name that appears "
        "in log _raw text (default: payment)."
    )


def exemplar_trace_failure_summary(records: list[ToolCallRecord]) -> str | None:
    """Return guidance when exemplar trace calls fail (often SignalFx GraphQL 503 under load)."""
    failures = [
        record
        for record in records
        if record.tool_name == "o11y_get_apm_exemplar_traces" and not record.success
    ]
    if not failures:
        return None
    messages = " ".join(record.error_message or "" for record in failures).lower()
    if "503" in messages or "graphql" in messages:
        return (
            f"{len(failures)} exemplar trace call(s) failed with SignalFx GraphQL errors (often 503 under "
            "concurrent load). Uncheck **Include exemplar traces** for capacity tests, or use ramp-up "
            "60–120s and dry-run with 1 participant first."
        )
    return (
        f"{len(failures)} exemplar trace call(s) failed — verify service/environment and exemplar_type "
        "(err for error alerts, lat_buck_ for latency)."
    )


def slowest_tool_by_p95(
    latency_by_tool: dict[str, dict[str, float | None]],
) -> tuple[str, float] | None:
    """Return (tool_name, p95_ms) for the slowest tool, if any."""
    slowest: tuple[str, float] | None = None
    for tool_name, stats in latency_by_tool.items():
        p95 = stats.get("p95_ms")
        if p95 is None:
            continue
        value = float(p95)
        if slowest is None or value > slowest[1]:
            slowest = (tool_name, value)
    return slowest


def suggest_next_participants(
    *,
    participants: int,
    error_rate_pct: float,
    use_o11y: bool,
    use_cloud: bool,
) -> str:
    """Human-readable capacity guidance after a run."""
    processes_per_participant = int(use_o11y) + int(use_cloud)
    if error_rate_pct > 5.0:
        return (
            f"Error rate {error_rate_pct}% — reduce participants, add ramp-up (30–120s), "
            "or investigate MCP gateway limits before scaling up."
        )

    milestones = [10, 20, 50, 100, 200]
    next_n = next((value for value in milestones if value > participants), None)
    if next_n is None:
        return (
            f"This run completed at {participants} participants ({error_rate_pct}% errors). "
            "You are at the configured participant maximum."
        )

    peak_processes = next_n * processes_per_participant
    if next_n <= LAPTOP_SOFT_LIMIT:
        return (
            f"0% errors at {participants} participants — try **{next_n}** next "
            f"(~{peak_processes} mcp-remote processes at peak)."
        )
    if next_n < EC2_RECOMMENDED_MIN_PARTICIPANTS:
        return (
            f"0% errors at {participants} — try **{next_n}** on a laptop with ramp-up 30s "
            f"(~{peak_processes} processes), or move to EC2 for headroom."
        )
    return (
        f"0% errors at {participants} — try **{next_n}** on r7i.4xlarge with "
        f"`ulimit -n 65535`, 60–120s ramp-up, and headless CLI (~{peak_processes} processes)."
    )


# Re-export load-test limits for suggestion text (avoid circular import from runner).
LAPTOP_SOFT_LIMIT = 20
EC2_RECOMMENDED_MIN_PARTICIPANTS = 50


def build_summary(
    *,
    participants: int,
    ramp_up_seconds: float,
    wall_clock_ms: float,
    participant_results: list[ParticipantResult],
    records: list[ToolCallRecord],
    run_config: RunConfigMetadata | None = None,
) -> RunSummary:
    total_calls = len(records)
    successful_calls = sum(1 for record in records if record.success)
    failed_calls = total_calls - successful_calls
    error_rate = (failed_calls / total_calls * 100.0) if total_calls else 0.0

    durations = [record.duration_ms for record in records if record.success]
    wall_seconds = wall_clock_ms / 1000.0 if wall_clock_ms > 0 else 0.0

    latency_by_tool: dict[str, list[float]] = {}
    server_stats: dict[str, dict[str, int | float]] = {}
    errors_by_type: dict[str, int] = {}

    first_failure_at: str | None = None
    for record in records:
        if not record.success:
            if first_failure_at is None or record.started_at < first_failure_at:
                first_failure_at = record.started_at
            error_type = record.error_type or "unknown"
            errors_by_type[error_type] = errors_by_type.get(error_type, 0) + 1

        if record.success:
            latency_by_tool.setdefault(record.tool_name, []).append(record.duration_ms)

        bucket = server_stats.setdefault(
            record.server,
            {"calls": 0, "errors": 0, "latency_p95_ms": None},
        )
        bucket["calls"] = int(bucket["calls"]) + 1
        if not record.success:
            bucket["errors"] = int(bucket["errors"]) + 1

    tool_latency_summary: dict[str, dict[str, float | None]] = {}
    for tool_name, tool_durations in latency_by_tool.items():
        tool_latency_summary[tool_name] = {
            "p50_ms": percentile(tool_durations, 50),
            "p95_ms": percentile(tool_durations, 95),
            "p99_ms": percentile(tool_durations, 99),
            "count": float(len(tool_durations)),
        }

    for server_name, bucket in server_stats.items():
        server_durations = [
            record.duration_ms
            for record in records
            if record.server == server_name and record.success
        ]
        bucket["latency_p95_ms"] = percentile(server_durations, 95)

    slowest = max(participant_results, key=lambda item: item.duration_ms, default=None)

    return RunSummary(
        participants=participants,
        ramp_up_seconds=ramp_up_seconds,
        wall_clock_ms=wall_clock_ms,
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        error_rate_pct=round(error_rate, 2),
        latency_p50_ms=percentile(durations, 50),
        latency_p95_ms=percentile(durations, 95),
        latency_p99_ms=percentile(durations, 99),
        calls_per_second=round(total_calls / wall_seconds, 2) if wall_seconds else 0.0,
        participants_per_second=round(participants / wall_seconds, 2) if wall_seconds else 0.0,
        slowest_participant_id=slowest.participant_id if slowest else None,
        slowest_participant_ms=slowest.duration_ms if slowest else None,
        first_failure_at=first_failure_at,
        latency_by_tool=tool_latency_summary,
        errors_by_type=errors_by_type,
        server_breakdown=server_stats,
        records=records,
        run_config=run_config,
    )


def records_to_csv(records: list[ToolCallRecord]) -> str:
    output = io.StringIO()
    fieldnames = list(ToolCallRecord.__dataclass_fields__.keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for record in records:
        writer.writerow(record.to_dict())
    return output.getvalue()


def summary_to_json(summary: RunSummary) -> str:
    return json.dumps(summary.to_dict(), indent=2, default=str)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
