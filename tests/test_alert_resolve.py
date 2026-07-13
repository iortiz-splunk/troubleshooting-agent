"""Tests for O11y alert ID resolution from MCP."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent

from workshop_shared.slack.alert_resolve import (
    _identifiers_from_alert,
    _pick_event_id,
    _pick_matching_alert,
    enrich_alert_context,
)


def test_pick_event_id_prefers_matching_rule() -> None:
    alerts = [
        {"id": "OLD123", "detectLabel": "other-detector", "active": True},
        {
            "id": "HMKipbjAwAI",
            "eventId": "HM_BrbSA0AA",
            "detectLabel": "ivortiz-high-latency-bad-capital",
            "active": True,
            "anomalyState": "anomalous",
        },
    ]
    event_id = _pick_event_id(
        alerts,
        {"rule": "ivortiz-high-latency-bad-capital", "service": "Verification"},
    )
    assert event_id == "HM_BrbSA0AA"


def test_pick_event_id_matches_alert_id_from_url() -> None:
    alerts = [
        {
            "id": "HM-8OmGA0AA",
            "eventId": "HM_BrbSA0AA",
            "detectLabel": "other-detector",
        },
    ]
    event_id = _pick_event_id(alerts, {"alert_id": "HM-8OmGA0AA"})
    assert event_id == "HM_BrbSA0AA"


def test_pick_matching_alert_fuzzy_rule_match() -> None:
    alerts = [
        {
            "id": "HMKipbjAwAI",
            "eventId": "HM_BrbSA0AA",
            "detectLabel": "Splunk Observability ivortiz-high-latency-bad-capital",
            "customProperties": {
                "sf_service": "Verification",
                "sf_environment": "Brian-E-AD-Capital",
            },
        },
    ]
    match = _pick_matching_alert(
        alerts,
        {
            "rule": "ivortiz-high-latency-bad-capital",
            "service": "Verification",
            "environment": "Brian-E-AD-Capital",
        },
    )
    assert match is not None
    assert _identifiers_from_alert(match)["event_id"] == "HM_BrbSA0AA"


def test_identifiers_from_alert_falls_back_to_incident_id() -> None:
    ids = _identifiers_from_alert(
        {"id": "HMKipbjAwAI", "incidentId": "CHkAbC123", "detectLabel": "latency"},
    )
    assert ids["incident_id"] == "CHkAbC123"
    assert ids["alert_id"] == "HMKipbjAwAI"
    assert "event_id" not in ids


@pytest.mark.asyncio
async def test_enrich_alert_context_resolves_via_mcp() -> None:
    settings = MagicMock()
    settings.enable_splunk_o11y = True

    mock_result = MagicMock()
    mock_result.isError = False
    mock_result.content = [
        TextContent(
            type="text",
            text=(
                '{"alerts":[{"id":"HMKipbjAwAI","eventId":"HM_BrbSA0AA",'
                '"detectLabel":"ivortiz-high-latency-bad-capital","active":true,'
                '"anomalyState":"anomalous"}]}'
            ),
        )
    ]

    mock_session = AsyncMock()
    mock_session.call_tool.return_value = mock_result

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session

    with (
        patch(
            "workshop_shared.slack.alert_resolve.splunk_o11y_gateway_params",
            return_value=MagicMock(),
        ),
        patch(
            "workshop_shared.slack.alert_resolve.connect_mcp_session",
            return_value=mock_cm,
        ),
    ):
        context = await enrich_alert_context(
            settings,
            {
                "service": "Verification",
                "environment": "Brian-E-AD-Capital",
                "rule": "ivortiz-high-latency-bad-capital",
            },
        )

    assert context["event_id"] == "HM_BrbSA0AA"
    mock_session.call_tool.assert_called()
    params = mock_session.call_tool.call_args.kwargs["arguments"]["params"]
    assert params["include_inactive"] is True
    assert params["limit"] == 500


@pytest.mark.asyncio
async def test_enrich_alert_context_widens_time_range_when_first_search_empty() -> None:
    settings = MagicMock()
    settings.enable_splunk_o11y = True

    empty = MagicMock()
    empty.isError = False
    empty.content = [TextContent(type="text", text='{"alerts":[]}')]

    hit = MagicMock()
    hit.isError = False
    hit.content = [
        TextContent(
            type="text",
            text=(
                '{"alerts":[{"id":"HMKipbjAwAI","eventId":"HM_BrbSA0AA",'
                '"detectLabel":"ivortiz-high-latency-bad-capital","active":true,'
                '"anomalyState":"anomalous"}]}'
            ),
        )
    ]

    def _call_tool(_name: str, *, arguments: dict) -> MagicMock:
        start = arguments["params"]["time_range"]["start"]
        return hit if start == "-1d" else empty

    mock_session = AsyncMock()
    mock_session.call_tool.side_effect = _call_tool

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session

    with (
        patch(
            "workshop_shared.slack.alert_resolve.splunk_o11y_gateway_params",
            return_value=MagicMock(),
        ),
        patch(
            "workshop_shared.slack.alert_resolve.connect_mcp_session",
            return_value=mock_cm,
        ),
    ):
        context = await enrich_alert_context(
            settings,
            {
                "service": "Verification",
                "environment": "Brian-E-AD-Capital",
                "rule": "ivortiz-high-latency-bad-capital",
            },
        )

    assert context["event_id"] == "HM_BrbSA0AA"
    assert mock_session.call_tool.call_count >= 3


@pytest.mark.asyncio
async def test_enrich_alert_context_sets_incident_id_without_event_id() -> None:
    settings = MagicMock()
    settings.enable_splunk_o11y = True

    mock_result = MagicMock()
    mock_result.isError = False
    mock_result.content = [
        TextContent(
            type="text",
            text=(
                '{"alerts":[{"id":"HMKipbjAwAI","incidentId":"CHkAbC123",'
                '"detectLabel":"ivortiz-high-latency-bad-capital","active":true}]}'
            ),
        )
    ]

    mock_session = AsyncMock()
    mock_session.call_tool.return_value = mock_result

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_session

    with (
        patch(
            "workshop_shared.slack.alert_resolve.splunk_o11y_gateway_params",
            return_value=MagicMock(),
        ),
        patch(
            "workshop_shared.slack.alert_resolve.connect_mcp_session",
            return_value=mock_cm,
        ),
    ):
        context = await enrich_alert_context(
            settings,
            {
                "service": "Verification",
                "rule": "ivortiz-high-latency-bad-capital",
            },
        )

    assert context["incident_id"] == "CHkAbC123"
    assert context["alert_id"] == "HMKipbjAwAI"
    assert "event_id" not in context
