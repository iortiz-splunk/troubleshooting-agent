"""Tests for Galileo session naming."""

from workshop_shared.observability.galileo import build_galileo_session_name


def test_galileo_session_name_uses_incident_id() -> None:
    name = build_galileo_session_name(
        "slack:1730000000.000100",
        {
            "incident_id": "CHkAbC123",
            "service": "Verification",
            "environment": "Brian-E-AD-Capital",
        },
    )
    assert name == "slack-alert-CHkAbC123 | Verification"


def test_galileo_session_name_prefers_event_id_over_alert_id() -> None:
    name = build_galileo_session_name(
        "slack:1783812037.760769",
        {
            "event_id": "HM_BrbSA0AA",
            "alert_id": "HM-8OmGA0AA",
            "incident_id": "CHkAbC123",
            "service": "Verification",
        },
    )
    assert name == "slack-alert-HM_BrbSA0AA | Verification"


def test_galileo_session_name_falls_back_to_alert_id_without_event_id() -> None:
    name = build_galileo_session_name(
        "slack:1783812037.760769",
        {
            "alert_id": "HM-8OmGA0AA",
            "service": "Verification",
        },
    )
    assert name == "slack-alert-HM-8OmGA0AA | Verification"


def test_galileo_session_name_falls_back_to_rule_name() -> None:
    name = build_galileo_session_name(
        "slack:1730000000.000100",
        {
            "service": "checkout-api",
            "rule": "ivortiz-high-latency-bad-capital",
        },
    )
    assert name == "slack-alert-ivortiz-high-latency-bad-capital | checkout-api"


def test_galileo_session_name_uses_event_id() -> None:
    name = build_galileo_session_name(
        "slack:1730000000.000100",
        {"event_id": "HM_BrbSA0AA", "service": "Verification"},
    )
    assert name == "slack-alert-HM_BrbSA0AA | Verification"


def test_galileo_session_name_for_cli_chat() -> None:
    name = build_galileo_session_name("chat:abc123def456", None)
    assert name == "chat-abc123def456"
