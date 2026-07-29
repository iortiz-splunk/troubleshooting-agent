"""Orchestrate concurrent virtual workshop participants."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from workshop_shared.config import Settings

from mcp_load_runner.diagnostics import get_logger
from mcp_load_runner.metrics import (
    ParticipantResult,
    RunConfigMetadata,
    RunProgress,
    RunSummary,
    ToolCallRecord,
    build_summary,
    utc_now_iso,
)
from mcp_load_runner.participant import build_steps_for_context, run_one_participant
from mcp_load_runner.scenarios import ScenarioContext
from mcp_load_runner.servers import McpServerSelection, apply_server_selection

MAX_PARTICIPANTS = 200
LAPTOP_SOFT_LIMIT = 20
EC2_RECOMMENDED_MIN_PARTICIPANTS = 50


@dataclass(frozen=True)
class LoadTestConfig:
    participants: int
    ramp_up_seconds: float = 0.0
    service_name: str = "Verification"
    environment_name: str = "Brian-E-AD-Capital"
    call_timeout_seconds: float = 60.0
    stop_on_first_error: bool = False
    server_selection: McpServerSelection = field(default_factory=McpServerSelection)

    def __post_init__(self) -> None:
        if self.participants < 1:
            msg = "participants must be at least 1"
            raise ValueError(msg)
        if self.participants > MAX_PARTICIPANTS:
            msg = f"participants must be at most {MAX_PARTICIPANTS}"
            raise ValueError(msg)


def estimated_mcp_subprocesses(participants: int, *, o11y: bool, cloud: bool) -> int:
    """Rough count of mcp-remote processes at peak (one stack per participant)."""
    per_participant = int(o11y) + int(cloud)
    return participants * per_participant


ProgressCallback = Callable[[RunProgress], None]
RecordCallback = Callable[[ToolCallRecord], None]


async def run_load_test(
    settings: Settings,
    config: LoadTestConfig,
    *,
    on_progress: ProgressCallback | None = None,
    on_record: RecordCallback | None = None,
) -> RunSummary:
    """Run N virtual participants with optional ramp-up between starts."""
    logger = get_logger()
    effective_settings = apply_server_selection(settings, config.server_selection)
    logger.info(
        "Starting load test: participants=%s ramp_up=%ss service=%r environment=%r servers=%s",
        config.participants,
        config.ramp_up_seconds,
        config.service_name,
        config.environment_name,
        config.server_selection.label,
    )
    context = ScenarioContext(
        service_name=config.service_name,
        environment_name=config.environment_name,
    )
    steps = build_steps_for_context(context, servers=config.server_selection)

    progress = RunProgress(total_participants=config.participants)
    if on_progress is not None:
        on_progress(progress)

    async def _run_participant(participant_id: int) -> ParticipantResult:
        progress.in_flight += 1
        if on_progress is not None:
            on_progress(progress)

        start = time.perf_counter()
        records, success, error_message = await run_one_participant(
            effective_settings,
            participant_id=participant_id,
            steps=steps,
            call_timeout_seconds=config.call_timeout_seconds,
            stop_on_first_error=config.stop_on_first_error,
            on_record=on_record,
        )
        duration_ms = (time.perf_counter() - start) * 1000.0

        progress.in_flight -= 1
        progress.completed += 1
        if not success:
            progress.failed += 1
        if on_progress is not None:
            on_progress(progress)

        return ParticipantResult(
            participant_id=participant_id,
            success=success,
            duration_ms=duration_ms,
            records=records,
            error_message=error_message,
        )

    async def _launch_with_ramp(participant_id: int) -> ParticipantResult:
        if config.ramp_up_seconds > 0 and config.participants > 1:
            delay = (participant_id - 1) * (config.ramp_up_seconds / config.participants)
            await asyncio.sleep(delay)
        return await _run_participant(participant_id)

    wall_start = time.perf_counter()
    results_raw = await asyncio.gather(
        *[_launch_with_ramp(participant_id) for participant_id in range(1, config.participants + 1)],
        return_exceptions=True,
    )
    wall_clock_ms = (time.perf_counter() - wall_start) * 1000.0

    participant_results: list[ParticipantResult] = []
    all_records: list[ToolCallRecord] = []

    for index, item in enumerate(results_raw, start=1):
        if isinstance(item, BaseException):
            message = str(item)
            failure = ParticipantResult(
                participant_id=index,
                success=False,
                duration_ms=0.0,
                error_message=message,
            )
            participant_results.append(failure)
            continue
        participant_results.append(item)
        all_records.extend(item.records)

    run_config = RunConfigMetadata(
        service_name=config.service_name,
        environment_name=config.environment_name,
        server_selection_label=config.server_selection.label,
        use_o11y=config.server_selection.use_o11y,
        use_cloud=config.server_selection.use_cloud,
        ramp_up_seconds=config.ramp_up_seconds,
        call_timeout_seconds=config.call_timeout_seconds,
        stop_on_first_error=config.stop_on_first_error,
        steps_per_participant=len(steps),
        finished_at=utc_now_iso(),
    )
    summary = build_summary(
        participants=config.participants,
        ramp_up_seconds=config.ramp_up_seconds,
        wall_clock_ms=wall_clock_ms,
        participant_results=participant_results,
        records=all_records,
        run_config=run_config,
    )
    logger.info(
        "Load test finished: error_rate=%s%% failed_calls=%s p95=%sms wall=%sms",
        summary.error_rate_pct,
        summary.failed_calls,
        summary.latency_p95_ms,
        summary.wall_clock_ms,
    )
    return summary
