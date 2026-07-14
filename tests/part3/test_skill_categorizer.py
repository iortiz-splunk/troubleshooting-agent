"""Tests for Part 3 alert categorizer."""

from part3_agent.skill_categorizer import categorize_alert


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
