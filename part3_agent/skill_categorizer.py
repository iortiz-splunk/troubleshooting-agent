"""Deterministic alert → product type categorization for Part 3."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PRODUCT_SKILL_MAP: dict[str, str] = {
    "apm": "troubleshoot-apm-incidents",
    "im": "troubleshoot-im-incidents",
    "rum": "troubleshoot-rum-incidents",
    "synthetics": "troubleshoot-synthetics-incidents",
}


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CategorizationResult:
    product_type: str
    skill_name: str | None


def _text_blob(alert: dict[str, Any]) -> str:
    parts = [
        str(alert.get("originatingMetric") or ""),
        str(alert.get("detector") or ""),
        str(alert.get("detectLabel") or ""),
    ]
    props = alert.get("customProperties")
    if isinstance(props, dict):
        parts.extend(str(v) for v in props.keys())
        parts.extend(str(v) for v in props.values())
    return " ".join(parts).lower()


def _metric_signals(alert: dict[str, Any]) -> str:
    return str(alert.get("originatingMetric") or "").lower()


def _has_sf_service(alert: dict[str, Any]) -> bool:
    props = alert.get("customProperties")
    if isinstance(props, dict) and props.get("sf_service"):
        return True
    return bool(alert.get("sf_service"))


def _im_signals(blob: str, metric: str) -> bool:
    im_metric_prefixes = ("k8s.", "system.", "container.", "memory.", "host.")
    if any(metric.startswith(p) for p in im_metric_prefixes):
        return True
    im_keywords = (
        "k8s.",
        "host.",
        "container.",
        "pod ",
        "crashloop",
        "imagepullbackoff",
        "cpu",
        "memory",
        "disk",
        "node",
        "namespace",
        "restarts",
    )
    return any(k in blob for k in im_keywords)


def _apm_signals(blob: str, metric: str, alert: dict[str, Any]) -> bool:
    if _has_sf_service(alert):
        return True
    apm_metrics = ("request.", "latency", "error", "throughput")
    if any(m in metric for m in apm_metrics):
        return True
    apm_keywords = ("service", "latency", "request", "dependency", "throughput", "apm")
    return any(k in blob for k in apm_keywords)


def _rum_signals(blob: str) -> bool:
    return bool(re.search(r"\brum\b|page load|browser|session|front-end|frontend", blob))


def _synthetics_signals(blob: str) -> bool:
    return bool(
        re.search(r"synthetic|synthetics|journey|uptime|availability check|check success", blob)
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def investigation_has_anchors(metadata: dict[str, str] | None) -> bool:
    """True when CLI/Slack context has enough signal to run an investigation anyway."""
    if not metadata:
        return False
    service = (metadata.get("service") or "").strip()
    rule = (metadata.get("rule") or metadata.get("detector") or "").strip()
    if service and (rule or (metadata.get("detector_id") or "").strip()):
        return True
    return any(
        (metadata.get(key) or "").strip()
        for key in ("event_id", "incident_id", "alert_id", "detector_id")
    )


def build_context_alert(
    metadata: dict[str, str] | None,
    *,
    user_message: str = "",
) -> dict[str, Any] | None:
    """Synthesize a minimal alert dict from parsed CLI/Slack metadata when MCP fetch fails."""
    meta = dict(metadata or {})
    if not meta.get("service") and user_message.strip():
        try:
            from workshop_shared.slack.messages import parse_o11y_alert_context

            for key, value in parse_o11y_alert_context(user_message).items():
                meta.setdefault(key, value)
        except ImportError:
            pass

    service = (meta.get("service") or "").strip()
    if not service:
        return None

    rule = (meta.get("rule") or meta.get("detector") or "").strip()
    environment = (meta.get("environment") or "").strip()
    alert: dict[str, Any] = {
        "detectLabel": rule,
        "detectorId": (meta.get("detector_id") or "").strip(),
        "customProperties": {"sf_service": service},
    }
    if environment:
        alert["customProperties"]["sf_environment"] = environment

    rule_lower = rule.lower()
    if "error" in rule_lower:
        alert["originatingMetric"] = "request.error"
    elif "latency" in rule_lower or "p99" in rule_lower or "p95" in rule_lower:
        alert["originatingMetric"] = "request.latency"
    elif "synthetic" in rule_lower or "uptime" in rule_lower:
        alert["originatingMetric"] = "synthetics.check"
    elif any(k in rule_lower for k in ("rum", "browser", "page load")):
        alert["originatingMetric"] = "rum.page"

    for key in ("event_id", "incident_id", "alert_id"):
        value = (meta.get(key) or "").strip()
        if not value:
            continue
        if key == "event_id":
            alert["eventId"] = value
        elif key == "incident_id":
            alert["incidentId"] = value
        else:
            alert["id"] = value

    return alert


def categorize_investigation(
    alert_payload: dict[str, Any] | None,
    metadata: dict[str, str] | None,
    *,
    user_message: str = "",
) -> CategorizationResult:
    """Categorize from MCP alert payload, or fall back to parsed investigation metadata."""
    alert = alert_payload or build_context_alert(metadata, user_message=user_message)
    result = categorize_alert(alert)
    if result.product_type != "unknown" or not investigation_has_anchors(metadata):
        return result

    rule = (metadata or {}).get("rule", "").lower()
    if _rum_signals(rule):
        return CategorizationResult(product_type="rum", skill_name=PRODUCT_SKILL_MAP["rum"])
    if _synthetics_signals(rule):
        return CategorizationResult(
            product_type="synthetics", skill_name=PRODUCT_SKILL_MAP["synthetics"]
        )
    if _im_signals(rule, rule) and not (metadata or {}).get("service"):
        return CategorizationResult(product_type="im", skill_name=PRODUCT_SKILL_MAP["im"])

    return CategorizationResult(product_type="apm", skill_name=PRODUCT_SKILL_MAP["apm"])


def categorize_alert(alert: dict[str, Any] | None) -> CategorizationResult:
    """
    Map alert JSON to product_type and skill_name using troubleshoot/reference.md rules.

    Order: IM metric/props → APM (sf_service) → RUM → Synthetics → unknown.
    """
    if not alert:
        return CategorizationResult(product_type="unknown", skill_name=None)

    blob = _text_blob(alert)
    metric = _metric_signals(alert)

    if _im_signals(blob, metric) and not _has_sf_service(alert):
        return CategorizationResult(product_type="im", skill_name=PRODUCT_SKILL_MAP["im"])

    if _apm_signals(blob, metric, alert):
        return CategorizationResult(product_type="apm", skill_name=PRODUCT_SKILL_MAP["apm"])

    if _rum_signals(blob):
        return CategorizationResult(product_type="rum", skill_name=PRODUCT_SKILL_MAP["rum"])

    if _synthetics_signals(blob):
        return CategorizationResult(
            product_type="synthetics", skill_name=PRODUCT_SKILL_MAP["synthetics"]
        )

    if _im_signals(blob, metric):
        return CategorizationResult(product_type="im", skill_name=PRODUCT_SKILL_MAP["im"])

    return CategorizationResult(product_type="unknown", skill_name=None)
