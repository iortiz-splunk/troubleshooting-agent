"""Tests for Slack alert message filtering and text extraction."""

from troubleshooting_agent.slack.listener import _build_investigation_prompt, _should_process_alert
from troubleshooting_agent.slack.messages import (
    extract_message_text,
    is_o11y_resolved_alert,
    is_o11y_stopped_alert,
    parse_o11y_alert_context,
    skip_reason,
)

O11Y_TRIGGERED_ALERT = """Splunk Observability Minor Alert: ivortiz-high-latency-bad-capital
Rule "ivortiz-high-latency-bad-capital" triggered at Wed, 1 Jul 2026 19:11:10 GMT.

Signal value for Verification in Brian-E-AD-Capital environment is out of bounds.

Signal details:
{sf_environment=Brian-E-AD-Capital, sf_service=Verification}"""

O11Y_STOPPED_ALERT = (
    "Stopped: ivortiz-high-latency-bad-capital (ivortiz-high-latency-bad-capital)\n"
    'Rule "ivortiz-high-latency-bad-capital" in detector "ivortiz-high-latency-bad-capital" '
    "was stopped at Wed, 1 Jul 2026 19:11:15 GMT UTC."
)


def test_processes_top_level_alert() -> None:
    event = {
        "text": "APM - latency spike - my-api:prod",
        "ts": "1000.1",
        "subtype": "bot_message",
    }
    assert _should_process_alert(event, our_bot_user_id="U_BOT")


def test_ignores_own_bot_messages() -> None:
    event = {"text": "investigating", "ts": "1", "user": "U_BOT"}
    assert not _should_process_alert(event, our_bot_user_id="U_BOT")


def test_ignores_thread_replies() -> None:
    event = {
        "text": "follow-up",
        "ts": "1000.2",
        "thread_ts": "1000.1",
    }
    assert not _should_process_alert(event, our_bot_user_id="U_BOT")


def test_extracts_attachment_only_alert() -> None:
    event = {
        "subtype": "bot_message",
        "ts": "1000.3",
        "attachments": [
            {
                "pretext": "Splunk Observability",
                "title": "High latency",
                "text": "service=my-api environment=prod",
                "fields": [{"title": "Severity", "value": "critical"}],
            }
        ],
    }
    text = extract_message_text(event)
    assert "High latency" in text
    assert "service=my-api environment=prod" in text
    assert "Severity: critical" in text
    assert skip_reason(event, our_bot_user_id="U_BOT") is None


def test_extracts_block_alert() -> None:
    event = {
        "subtype": "bot_message",
        "ts": "1000.4",
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Detector*: error rate on checkout"},
            }
        ],
    }
    text = extract_message_text(event)
    assert "error rate on checkout" in text
    assert skip_reason(event, our_bot_user_id="U_BOT") is None


def test_parses_o11y_cloud_alert_context() -> None:
    context = parse_o11y_alert_context(O11Y_TRIGGERED_ALERT)
    assert context["service"] == "Verification"
    assert context["environment"] == "Brian-E-AD-Capital"
    assert context["rule"] == "ivortiz-high-latency-bad-capital"
    assert context["severity"] == "Minor"
    prompt = _build_investigation_prompt(O11Y_TRIGGERED_ALERT)
    assert "Verification" in prompt
    assert "Brian-E-AD-Capital" in prompt


def test_skips_o11y_stopped_alerts() -> None:
    assert is_o11y_resolved_alert(O11Y_STOPPED_ALERT)
    event = {"text": O11Y_STOPPED_ALERT, "ts": "2000.1", "subtype": "bot_message"}
    assert skip_reason(event, our_bot_user_id="U_BOT") == "o11y_resolved_alert"
    assert not _should_process_alert(event, our_bot_user_id="U_BOT")


def test_skips_o11y_resolved_when_stopped_not_first_line() -> None:
    """Splunk often puts metadata before the Stopped: line in extracted text."""
    event = {
        "subtype": "bot_message",
        "ts": "2000.2",
        "attachments": [
            {
                "pretext": "Added by Splunk Observability Cloud, US1",
                "title": "Stopped: ivortiz-high-latency-bad-capital",
                "text": (
                    'Rule "ivortiz-high-latency-bad-capital" was stopped at '
                    "Wed, 1 Jul 2026 19:11:15 GMT UTC."
                ),
            }
        ],
    }
    assert skip_reason(event, our_bot_user_id="U_BOT") == "o11y_resolved_alert"


def test_skips_o11y_resolved_prefix_variants() -> None:
    for prefix in ("Resolved:", "Cleared:", "Recovered:"):
        event = {"text": f"{prefix} latency detector", "ts": "2000.3"}
        assert skip_reason(event, our_bot_user_id="U_BOT") == "o11y_resolved_alert"


def test_skips_o11y_ok_alert_line() -> None:
    text = "Splunk Observability OK Alert: ivortiz-high-latency-bad-capital\nCondition cleared."
    event = {"text": text, "ts": "2000.4"}
    assert is_o11y_stopped_alert(text)
    assert skip_reason(event, our_bot_user_id="U_BOT") == "o11y_resolved_alert"


def test_processes_o11y_triggered_after_metadata_lines() -> None:
    event = {
        "subtype": "bot_message",
        "ts": "2000.5",
        "attachments": [
            {
                "pretext": "Added by Splunk Observability Cloud, US1",
                "text": O11Y_TRIGGERED_ALERT,
            }
        ],
    }
    assert skip_reason(event, our_bot_user_id="U_BOT") is None
