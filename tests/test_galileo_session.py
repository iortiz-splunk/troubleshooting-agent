"""Tests for Galileo session naming."""

from workshop_shared.observability.galileo import build_galileo_session_name


def test_galileo_session_name_uses_incident_id_and_workshop_part() -> None:
    name = build_galileo_session_name(
        "slack:1730000000.000100",
        {
            "incident_id": "CHkAbC123",
            "service": "Verification",
            "environment": "Brian-E-AD-Capital",
            "workshop_part": "part2_agent",
        },
    )
    assert name == "slack-alert-CHkAbC123 | part2_agent"


def test_galileo_session_name_prefers_event_id_over_alert_id() -> None:
    name = build_galileo_session_name(
        "slack:1783812037.760769",
        {
            "event_id": "HM_BrbSA0AA",
            "alert_id": "HM-8OmGA0AA",
            "incident_id": "CHkAbC123",
            "service": "Verification",
            "workshop_part": "part3_agent",
        },
    )
    assert name == "slack-alert-HM_BrbSA0AA | part3_agent"


def test_galileo_session_name_falls_back_to_alert_id_without_event_id() -> None:
    name = build_galileo_session_name(
        "slack:1783812037.760769",
        {
            "alert_id": "HM-8OmGA0AA",
            "service": "Verification",
            "workshop_part": "part1_agent",
        },
    )
    assert name == "slack-alert-HM-8OmGA0AA | part1_agent"


def test_galileo_session_name_falls_back_to_service_without_workshop_part() -> None:
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
        {
            "event_id": "HM_BrbSA0AA",
            "service": "Verification",
            "workshop_part": "part2",
        },
    )
    assert name == "slack-alert-HM_BrbSA0AA | part2_agent"


def test_galileo_session_name_for_cli_chat() -> None:
    name = build_galileo_session_name(
        "chat:abc123def456",
        {"workshop_part": "part1_agent"},
    )
    assert name == "chat-abc123def456 | part1_agent"


def test_galileo_session_name_for_cli_chat_without_part() -> None:
    name = build_galileo_session_name("chat:abc123def456", None)
    assert name == "chat-abc123def456"
