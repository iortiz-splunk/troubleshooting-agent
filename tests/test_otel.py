"""Tests for Splunk OTel bootstrap (no heavy deps required)."""

from troubleshooting_agent.config import Settings
from troubleshooting_agent.observability.otel import init_splunk_otel


def test_init_splunk_otel_disabled() -> None:
    settings = Settings(enable_splunk_otel=False)
    assert init_splunk_otel(settings) is False
