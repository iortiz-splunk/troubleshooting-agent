"""Scripted MCP tool sequences for load testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mcp_load_runner.servers import McpServerSelection


DEFAULT_SERVICE_NAME = "Verification"
DEFAULT_ENVIRONMENT_NAME = "Brian-E-AD-Capital"
DEFAULT_INDEX = "k8s-apps"


@dataclass(frozen=True)
class ToolStep:
    step: int
    tool_name: str
    server: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ScenarioContext:
    service_name: str = DEFAULT_SERVICE_NAME
    environment_name: str = DEFAULT_ENVIRONMENT_NAME
    time_range: dict[str, str] = field(default_factory=lambda: {"start": "-1h", "stop": "now"})


def _apm_params(context: ScenarioContext) -> dict[str, Any]:
    return {
        "service_name": context.service_name,
        "environment_name": context.environment_name,
        "time_range": context.time_range,
    }


def _splunk_log_query(context: ScenarioContext) -> str:
    service = context.service_name.replace('"', "")
    return (
        f'index={DEFAULT_INDEX} earliest=-1h latest=now '
        f'(sourcetype=httpevent OR sourcetype="kube:container:*") '
        f'_raw="*{service}*" '
        "| head 20"
    )


def build_part3_apm_scenario(
    context: ScenarioContext | None = None,
    *,
    servers: McpServerSelection | None = None,
) -> list[ToolStep]:
    """Part 3 APM investigation tool path (identify + investigate, no LLM)."""
    ctx = context or ScenarioContext()
    selection = servers or McpServerSelection()
    params = _apm_params(ctx)
    spl_query = _splunk_log_query(ctx)

    steps: list[ToolStep] = []
    if selection.use_o11y:
        steps.extend(
            [
                ToolStep(
                    step=0,
                    tool_name="o11y_search_alerts_or_incidents",
                    server="splunk_o11y",
                    arguments={"params": params},
                ),
                ToolStep(
                    step=0,
                    tool_name="o11y_get_apm_services",
                    server="splunk_o11y",
                    arguments={"params": params},
                ),
                ToolStep(
                    step=0,
                    tool_name="o11y_get_apm_service_latency",
                    server="splunk_o11y",
                    arguments={"params": params},
                ),
                ToolStep(
                    step=0,
                    tool_name="o11y_get_apm_service_errors_and_requests",
                    server="splunk_o11y",
                    arguments={"params": params},
                ),
                ToolStep(
                    step=0,
                    tool_name="o11y_get_apm_exemplar_traces",
                    server="splunk_o11y",
                    arguments={"params": {**params, "exemplar_type": "lat_buck_"}},
                ),
            ]
        )
    if selection.use_cloud:
        steps.append(
            ToolStep(
                step=0,
                tool_name="splunk_run_query",
                server="splunk_cloud_mcp",
                arguments={
                    "query": spl_query,
                    "earliest_time": "-1h",
                    "latest_time": "now",
                    "row_limit": 20,
                },
            )
        )

    return [
        ToolStep(
            step=index,
            tool_name=step.tool_name,
            server=step.server,
            arguments=step.arguments,
        )
        for index, step in enumerate(steps, start=1)
    ]


def required_tool_names(servers: McpServerSelection | None = None) -> set[str]:
    return {step.tool_name for step in build_part3_apm_scenario(servers=servers)}
