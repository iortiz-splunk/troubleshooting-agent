"""Tests for Part 3 alert categorizer."""

from part3_agent.skill_categorizer import (
    build_context_alert,
    categorize_alert,
    categorize_investigation,
    investigation_has_anchors,
)


def test_categorize_apm_by_sf_service() -> None:
    alert = {
        "originatingMetric": "request.latency",
        "detectLabel": "Service latency high",
        "customProperties": {"sf_service": "checkout-api", "sf_environment": "prod"},
    }
    result = categorize_alert(alert)
    assert result.product_type == "apm"
    assert result.skill_name == "troubleshoot-apm-incidents"


def test_categorize_im_by_k8s_metric() -> None:
    alert = {
        "originatingMetric": "k8s.container.restarts",
        "detectLabel": "Pod Restart High",
        "customProperties": {"k8s.pod.name": "api-123"},
    }
    result = categorize_alert(alert)
    assert result.product_type == "im"
    assert result.skill_name == "troubleshoot-im-incidents"


def test_categorize_rum() -> None:
    alert = {
        "originatingMetric": "rum.page.load",
        "detectLabel": "RUM page load degraded",
        "customProperties": {"rum.app": "web-store"},
    }
    result = categorize_alert(alert)
    assert result.product_type == "rum"
    assert result.skill_name == "troubleshoot-rum-incidents"


def test_categorize_synthetics() -> None:
    alert = {
        "originatingMetric": "synthetic.check.success",
        "detectLabel": "Synthetic journey failed",
        "customProperties": {"check.name": "homepage"},
    }
    result = categorize_alert(alert)
    assert result.product_type == "synthetics"
    assert result.skill_name == "troubleshoot-synthetics-incidents"


def test_categorize_unknown_when_empty() -> None:
    result = categorize_alert(None)
    assert result.product_type == "unknown"
    assert result.skill_name is None


def test_investigation_has_anchors_payment_workshop() -> None:
    metadata = {
        "service": "payment",
        "environment": "sre-agent-workshop",
        "detector_id": "HNcv52_AwAA",
        "rule": "SRE Agent - PaymentService High Error Rate",
    }
    assert investigation_has_anchors(metadata) is True


def test_build_context_alert_from_workshop_metadata() -> None:
    alert = build_context_alert(
        {
            "service": "payment",
            "environment": "sre-agent-workshop",
            "detector_id": "HNcv52_AwAA",
            "rule": "SRE Agent - PaymentService High Error Rate",
        }
    )
    assert alert is not None
    assert alert["customProperties"]["sf_service"] == "payment"
    assert alert["originatingMetric"] == "request.error"


def test_categorize_investigation_without_mcp_payload() -> None:
    metadata = {
        "service": "payment",
        "environment": "sre-agent-workshop",
        "detector_id": "HNcv52_AwAA",
        "rule": "SRE Agent - PaymentService High Error Rate",
    }
    result = categorize_investigation(None, metadata)
    assert result.product_type == "apm"
    assert result.skill_name == "troubleshoot-apm-incidents"
