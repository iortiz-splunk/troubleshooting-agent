"""Tests for MCP load runner scenarios."""

from mcp_load_runner.scenarios import ScenarioContext, build_part3_apm_scenario, required_tool_names
from mcp_load_runner.servers import McpServerSelection


def test_part3_apm_scenario_has_six_steps() -> None:
    steps = build_part3_apm_scenario(
        servers=McpServerSelection(use_o11y=True, use_cloud=True),
    )
    assert len(steps) == 6
    assert steps[0].tool_name == "o11y_search_alerts_or_incidents"
    assert steps[4].arguments["params"]["exemplar_type"] == "lat_buck_"
    assert steps[5].tool_name == "splunk_run_query"


def test_part3_apm_scenario_o11y_only() -> None:
    steps = build_part3_apm_scenario(
        servers=McpServerSelection(use_o11y=True, use_cloud=False),
    )
    assert len(steps) == 5
    assert all(step.server == "splunk_o11y" for step in steps)
    assert {step.tool_name for step in steps} == required_tool_names(
        McpServerSelection(use_o11y=True, use_cloud=False)
    )


def test_scenario_uses_nested_params() -> None:
    context = ScenarioContext(service_name="api", environment_name="prod")
    params = build_part3_apm_scenario(context)[1].arguments["params"]
    assert params["service_name"] == "api"
    assert params["environment_name"] == "prod"
    assert params["time_range"] == {"start": "-1h", "stop": "now"}


def test_required_tool_names() -> None:
    names = required_tool_names(McpServerSelection(use_o11y=True, use_cloud=True))
    assert "o11y_get_apm_exemplar_traces" in names
    assert "splunk_run_query" in names

    o11y_only = required_tool_names(McpServerSelection(use_o11y=True, use_cloud=False))
    assert "splunk_run_query" not in o11y_only
    assert len(o11y_only) == 5
