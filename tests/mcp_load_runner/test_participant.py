"""Tests for MCP load runner participant execution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_load_runner.participant import run_one_participant
from mcp_load_runner.runner import LoadTestConfig, estimated_mcp_subprocesses
from mcp_load_runner.scenarios import ToolStep
from workshop_shared.config import Settings


@pytest.mark.asyncio
async def test_participant_records_tool_failure() -> None:
    settings = Settings()
    steps = [
        ToolStep(
            step=1,
            tool_name="o11y_get_apm_services",
            server="splunk_o11y",
            arguments={"params": {"service_name": "api", "environment_name": "prod"}},
        )
    ]

    mock_tool = MagicMock()
    mock_tool.name = "o11y_get_apm_services"
    mock_tool.ainvoke = AsyncMock(return_value="ERROR: validation failed")

    mock_manager = MagicMock()
    mock_manager.langchain_tools = [mock_tool]
    mock_manager.__aenter__ = AsyncMock(return_value=mock_manager)
    mock_manager.__aexit__ = AsyncMock(return_value=None)

    with patch("mcp_load_runner.participant.McpSessionManager", return_value=mock_manager):
        records, success, error = await run_one_participant(
            settings,
            participant_id=1,
            steps=steps,
        )

    assert success is False
    assert error is not None
    assert len(records) == 1
    assert records[0].success is False
    assert records[0].error_type == "validation"


def test_estimated_mcp_subprocesses() -> None:
    assert estimated_mcp_subprocesses(200, o11y=True, cloud=True) == 400
    assert estimated_mcp_subprocesses(10, o11y=True, cloud=False) == 10


@pytest.mark.asyncio
@pytest.mark.mcp_integration
async def test_run_load_test_smoke_one_participant() -> None:
    settings = Settings()
    if not settings.enable_splunk_o11y or not settings.enable_splunk_cloud_mcp:
        pytest.skip("ENABLE_SPLUNK_O11Y and ENABLE_SPLUNK_CLOUD_MCP required")

    from mcp_load_runner.runner import run_load_test

    summary = await run_load_test(
        settings,
        LoadTestConfig(participants=1, ramp_up_seconds=0.0),
    )
    assert summary.participants == 1
    assert summary.total_calls >= 1
