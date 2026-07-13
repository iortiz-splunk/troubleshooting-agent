"""Resolve O11y alert IDs when Slack messages omit alert-details URLs."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp import ClientSession

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import _normalize_mcp_arguments
from workshop_shared.mcp.connect import connect_mcp_session
from workshop_shared.mcp.gateway import splunk_o11y_gateway_params

_logger = logging.getLogger("workshop_shared")

# Widen the search window when the first query returns no alerts (matches get-alerts skill).
_TIME_RANGE_LADDER = ("-1h", "-6h", "-1d", "-3d", "-7d")
_DEFAULT_ALERT_LIMIT = 500


def _pick_event_id(alerts: list[dict[str, Any]], context: dict[str, str]) -> str | None:
    """Choose the O11y eventId from MCP search results for this Slack notification."""
    alert = _pick_matching_alert(alerts, context)
    if alert is None:
        return None
    return _identifiers_from_alert(alert).get("event_id")


def _alert_sort_key(alert: dict[str, Any]) -> int:
    ts = alert.get("anomalyStateUpdateTimestampMs")
    if isinstance(ts, (int, float)):
        return int(ts)
    return 0


def _alert_rule_label(alert: dict[str, Any]) -> str:
    return str(alert.get("detectLabel") or alert.get("detector") or "").strip().lower()


def _name_matches(label: str, expected: str) -> bool:
    if not label or not expected:
        return False
    label_l = label.lower()
    expected_l = expected.lower()
    return label_l == expected_l or expected_l in label_l or label_l in expected_l


def _matches_rule(alert: dict[str, Any], context: dict[str, str]) -> bool:
    label = _alert_rule_label(alert)
    if not label:
        return False
    rule = (context.get("rule") or "").strip()
    detector = (context.get("detector") or "").strip()
    return _name_matches(label, rule) or _name_matches(label, detector)


def _custom_properties(alert: dict[str, Any]) -> dict[str, Any]:
    props = alert.get("customProperties")
    return props if isinstance(props, dict) else {}


def _matches_service_env(alert: dict[str, Any], context: dict[str, str]) -> bool:
    props = _custom_properties(alert)
    service = (context.get("service") or "").strip()
    environment = (context.get("environment") or "").strip()
    if service:
        alert_service = str(props.get("sf_service") or alert.get("sf_service") or "").strip()
        if alert_service and alert_service != service:
            return False
    if environment:
        alert_env = str(props.get("sf_environment") or alert.get("sf_environment") or "").strip()
        if alert_env and alert_env != environment:
            return False
    return bool(service or environment)


def _pick_matching_alert(
    alerts: list[dict[str, Any]],
    context: dict[str, str],
) -> dict[str, Any] | None:
    """Pick the best alert row for this Slack notification."""
    if not alerts:
        return None

    sorted_alerts = sorted(alerts, key=_alert_sort_key, reverse=True)

    for alert in sorted_alerts:
        if _matches_rule(alert, context) and _matches_service_env(alert, context):
            return alert

    for alert in sorted_alerts:
        if _matches_rule(alert, context):
            return alert

    alert_id = (context.get("alert_id") or "").strip()
    if alert_id:
        for alert in sorted_alerts:
            for key in ("eventId", "event_id", "id"):
                value = alert.get(key)
                if isinstance(value, str) and _ids_equivalent(value, alert_id):
                    return alert

    for alert in sorted_alerts:
        if _matches_service_env(alert, context) and alert.get("active"):
            return alert

    for alert in sorted_alerts:
        if alert.get("active") and alert.get("anomalyState") == "anomalous":
            return alert

    return sorted_alerts[0]


def _identifiers_from_alert(alert: dict[str, Any]) -> dict[str, str]:
    """Extract Galileo-friendly identifiers from an MCP alert record."""
    ids: dict[str, str] = {}

    event_id = _event_id_from_record(alert)
    if event_id:
        ids["event_id"] = event_id

    incident_id = alert.get("incidentId")
    if isinstance(incident_id, str) and incident_id.strip():
        ids["incident_id"] = incident_id.strip()

    alert_id = alert.get("id")
    if isinstance(alert_id, str) and alert_id.strip():
        ids["alert_id"] = alert_id.strip()

    return ids


def _ids_equivalent(left: str, right: str) -> bool:
    """Compare O11y ids that may differ only by hyphen vs underscore."""
    return left.strip().replace("-", "_").lower() == right.strip().replace("-", "_").lower()


def _event_id_from_record(alert: dict[str, Any]) -> str | None:
    for key in ("eventId", "event_id"):
        value = alert.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _parse_mcp_alerts_payload(text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    alerts = payload.get("alerts") if isinstance(payload, dict) else None
    if not isinstance(alerts, list):
        return []
    return [item for item in alerts if isinstance(item, dict)]


def _base_search_params(*, time_start: str) -> dict[str, Any]:
    return {
        "time_range": {"start": time_start, "stop": "now"},
        "include_inactive": True,
        "limit": _DEFAULT_ALERT_LIMIT,
    }


def _search_param_strategies(context: dict[str, str]) -> list[dict[str, Any]]:
    """Build progressively broader MCP search strategies."""
    strategies: list[dict[str, Any]] = []
    service = (context.get("service") or "").strip()
    environment = (context.get("environment") or "").strip()
    rule = (context.get("rule") or "").strip()

    for time_start in _TIME_RANGE_LADDER:
        if service:
            with_env = {**_base_search_params(time_start=time_start), "service_name": service}
            if environment:
                with_env["environments"] = [environment]
            strategies.append(with_env)

            if environment:
                service_only = {
                    **_base_search_params(time_start=time_start),
                    "service_name": service,
                }
                strategies.append(service_only)

        if rule:
            keyword_search = {
                **_base_search_params(time_start=time_start),
                "keywords": rule,
            }
            strategies.append(keyword_search)
            if service:
                strategies.append(
                    {
                        **_base_search_params(time_start=time_start),
                        "keywords": rule,
                        "service_name": service,
                    }
                )

    # De-dupe identical param dicts while preserving order.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for params in strategies:
        key = json.dumps(params, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(params)
    return unique


async def _search_alerts(session: ClientSession, params: dict[str, Any]) -> list[dict[str, Any]]:
    arguments = _normalize_mcp_arguments(None, {"params": params})
    result = await session.call_tool("o11y_search_alerts_or_incidents", arguments=arguments)
    if result.isError:
        _logger.debug("MCP alert search returned isError params=%s", params)
        return []

    parts: list[str] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            parts.append(text)
    if not parts:
        return []
    return _parse_mcp_alerts_payload("\n".join(parts))


async def _resolve_identifiers_via_mcp(
    session: ClientSession,
    context: dict[str, str],
) -> dict[str, str]:
    """Search alerts with progressively broader filters until identifiers are found."""
    for attempt, params in enumerate(_search_param_strategies(context)):
        alerts = await _search_alerts(session, params)
        _logger.debug(
            "MCP alert search attempt=%s alerts=%s time_range=%s service=%s env=%s keywords=%s",
            attempt,
            len(alerts),
            params.get("time_range"),
            params.get("service_name"),
            params.get("environments"),
            params.get("keywords"),
        )
        alert = _pick_matching_alert(alerts, context)
        if alert is None:
            continue
        identifiers = _identifiers_from_alert(alert)
        if identifiers:
            return identifiers
    return {}


async def enrich_alert_context(
    settings: Settings,
    context: dict[str, str],
) -> dict[str, str]:
    """
    Fill event_id (O11y eventId) via MCP when Slack text lacks it.

    Also sets incident_id / alert_id when present so Galileo can name sessions
    even if eventId is missing from the MCP payload.
    """
    if context.get("event_id") or not settings.enable_splunk_o11y:
        return context

    service = context.get("service")
    if not service and not context.get("rule"):
        return context

    try:
        async with connect_mcp_session(splunk_o11y_gateway_params(settings)) as session:
            identifiers = await _resolve_identifiers_via_mcp(session, context)
    except Exception:
        _logger.warning("Could not resolve O11y identifiers via MCP", exc_info=True)
        return context

    if not identifiers:
        _logger.warning(
            "Could not resolve O11y identifiers via MCP for service=%s env=%s rule=%s",
            context.get("service"),
            context.get("environment"),
            context.get("rule"),
        )
        return context

    enriched = {**context}
    for key, value in identifiers.items():
        if not enriched.get(key):
            enriched[key] = value

    _logger.info(
        "Resolved O11y identifiers via MCP: %s",
        ", ".join(f"{key}={value}" for key, value in identifiers.items()),
    )
    return enriched
