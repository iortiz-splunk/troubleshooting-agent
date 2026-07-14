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
