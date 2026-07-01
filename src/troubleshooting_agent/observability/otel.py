"""Splunk OpenTelemetry bootstrap and manual spans."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from troubleshooting_agent.config import Settings

_logger = logging.getLogger("troubleshooting_agent")
_otel_initialized = False


def init_splunk_otel(settings: Settings) -> bool:
    """Start Splunk OTel distro (idempotent). Returns True when active."""
    global _otel_initialized
    if not settings.enable_splunk_otel or _otel_initialized:
        return _otel_initialized

    try:
        from splunk_opentelemetry import start as splunk_start
    except ImportError:
        _logger.warning(
            "ENABLE_SPLUNK_OTEL=true but splunk-opentelemetry is not installed. "
            'Run: pip install "troubleshooting-agent[observability]"'
        )
        return False

    os.environ.setdefault("OTEL_SERVICE_NAME", settings.otel_service_name)
    if settings.splunk_access_token:
        os.environ.setdefault("SPLUNK_ACCESS_TOKEN", settings.splunk_access_token)
    if settings.splunk_o11y_realm:
        os.environ.setdefault("SPLUNK_REALM", settings.splunk_o11y_realm)

    splunk_start()
    _init_httpx_instrumentation()
    _otel_initialized = True
    _logger.info("Splunk OTel initialized service=%s", settings.otel_service_name)
    return True


def _init_httpx_instrumentation() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        _logger.debug("opentelemetry-instrumentation-httpx not installed; LLM HTTP spans skipped")


def otel_active() -> bool:
    return _otel_initialized


@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Manual span when Splunk OTel is active; no-op otherwise."""
    if not _otel_initialized:
        yield None
        return

    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("troubleshooting_agent")
        with tracer.start_as_current_span(name, attributes=attributes or {}) as current:
            yield current
    except Exception:
        yield None
