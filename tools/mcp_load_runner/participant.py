"""Execute one virtual workshop participant against MCP servers."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from langchain_core.tools import BaseTool

from workshop_shared.config import Settings
from workshop_shared.mcp.session import McpSessionManager

from mcp_load_runner.diagnostics import get_logger
from mcp_load_runner.metrics import (
    ToolCallRecord,
    classify_error,
    truncate_message,
    utc_now_iso,
)
from mcp_load_runner.scenarios import ScenarioContext, ToolStep, build_part3_apm_scenario
from mcp_load_runner.servers import McpServerSelection


async def run_one_participant(
    settings: Settings,
    *,
    participant_id: int,
    steps: list[ToolStep] | None = None,
    call_timeout_seconds: float = 60.0,
    stop_on_first_error: bool = False,
    on_record: Callable[[ToolCallRecord], None] | None = None,
) -> tuple[list[ToolCallRecord], bool, str | None]:
    """
    Run the scripted tool sequence for one participant.

    Returns (records, overall_success, error_message).
    """
    sequence = steps or build_part3_apm_scenario()
    records: list[ToolCallRecord] = []
    participant_error: str | None = None
    logger = get_logger()

    try:
        logger.info("Participant %s: opening MCP sessions", participant_id)
        async with McpSessionManager(settings) as manager:
            tools_by_name = {tool.name: tool for tool in manager.langchain_tools}
            logger.info(
                "Participant %s: loaded %d tool(s): %s",
                participant_id,
                len(tools_by_name),
                ", ".join(sorted(tools_by_name)),
            )

            for step in sequence:
                record = await _invoke_step(
                    participant_id=participant_id,
                    step=step,
                    tools_by_name=tools_by_name,
                    timeout_seconds=call_timeout_seconds,
                )
                records.append(record)
                if on_record is not None:
                    on_record(record)

                if not record.success:
                    participant_error = record.error_message
                    logger.warning(
                        "Participant %s step %s (%s): %s",
                        participant_id,
                        step.step,
                        step.tool_name,
                        participant_error,
                    )
                    if stop_on_first_error:
                        break
                else:
                    logger.info(
                        "Participant %s step %s (%s): OK in %.0fms",
                        participant_id,
                        step.step,
                        step.tool_name,
                        record.duration_ms,
                    )
    except Exception as exc:
        participant_error = truncate_message(str(exc))
        logger.error("Participant %s session failed: %s", participant_id, participant_error)
        if records:
            return records, False, participant_error
        records.append(
            ToolCallRecord(
                participant_id=participant_id,
                step=0,
                tool_name="session",
                server="mcp_session",
                started_at=utc_now_iso(),
                duration_ms=0.0,
                success=False,
                error_type=classify_error(participant_error),
                error_message=participant_error,
            )
        )
        if on_record is not None:
            on_record(records[-1])
        return records, False, participant_error

    overall_success = all(record.success for record in records)
    return records, overall_success, participant_error


async def _invoke_step(
    *,
    participant_id: int,
    step: ToolStep,
    tools_by_name: dict[str, BaseTool],
    timeout_seconds: float,
) -> ToolCallRecord:
    started_at = utc_now_iso()
    start = time.perf_counter()
    tool = tools_by_name.get(step.tool_name)

    if tool is None:
        message = truncate_message(f"Tool not found: {step.tool_name}")
        return ToolCallRecord(
            participant_id=participant_id,
            step=step.step,
            tool_name=step.tool_name,
            server=step.server,
            started_at=started_at,
            duration_ms=0.0,
            success=False,
            error_type="tool_not_found",
            error_message=message,
        )

    try:
        result = await asyncio.wait_for(
            tool.ainvoke(step.arguments),
            timeout=timeout_seconds,
        )
        duration_ms = (time.perf_counter() - start) * 1000.0
        response_text = _result_text(result)
        if response_text.startswith("ERROR:"):
            error_message = truncate_message(response_text)
            return ToolCallRecord(
                participant_id=participant_id,
                step=step.step,
                tool_name=step.tool_name,
                server=step.server,
                started_at=started_at,
                duration_ms=duration_ms,
                success=False,
                error_type=classify_error(error_message),
                error_message=error_message,
                response_bytes=len(response_text.encode("utf-8")),
            )

        return ToolCallRecord(
            participant_id=participant_id,
            step=step.step,
            tool_name=step.tool_name,
            server=step.server,
            started_at=started_at,
            duration_ms=duration_ms,
            success=True,
            response_bytes=len(response_text.encode("utf-8")),
        )
    except TimeoutError:
        duration_ms = (time.perf_counter() - start) * 1000.0
        message = truncate_message(f"Timeout after {timeout_seconds}s")
        return ToolCallRecord(
            participant_id=participant_id,
            step=step.step,
            tool_name=step.tool_name,
            server=step.server,
            started_at=started_at,
            duration_ms=duration_ms,
            success=False,
            error_type="timeout",
            error_message=message,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000.0
        message = truncate_message(str(exc))
        return ToolCallRecord(
            participant_id=participant_id,
            step=step.step,
            tool_name=step.tool_name,
            server=step.server,
            started_at=started_at,
            duration_ms=duration_ms,
            success=False,
            error_type=classify_error(message),
            error_message=message,
        )


def _result_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    return str(result)


def build_steps_for_context(
    context: ScenarioContext,
    *,
    servers: McpServerSelection | None = None,
) -> list[ToolStep]:
    return build_part3_apm_scenario(context, servers=servers)
