"""Splunk OpenTelemetry bootstrap and manual spans."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from workshop_shared.config import Settings

_logger = logging.getLogger("workshop_shared")
_otel_initialized = False

# ---------------------------------------------------------------------------
# Splunk OTel bootstrap
# Starts the Splunk distro once; sets env vars for direct ingest when configured.
# ---------------------------------------------------------------------------


def init_splunk_otel(settings: Settings) -> bool:
    """Start Splunk OTel distro (idempotent). Returns True when active."""
    global _otel_initialized
    if not settings.enable_splunk_otel or _otel_initialized:
        return _otel_initialized

    os.environ.setdefault("OTEL_SERVICE_NAME", settings.otel_service_name)
    if settings.splunk_access_token:
        os.environ.setdefault("SPLUNK_ACCESS_TOKEN", settings.splunk_access_token)
    if settings.splunk_o11y_realm:
        os.environ.setdefault("SPLUNK_REALM", settings.splunk_o11y_realm)
    # Splunk distro enables OTLP log export by default (localhost:4318). We only need APM traces.
    os.environ.setdefault("OTEL_LOGS_EXPORTER", "none")

    try:
        # splunk-opentelemetry 2.x (current)
        from splunk_otel import init_splunk_otel as splunk_start

        splunk_start()
    except ImportError:
        try:
            # splunk-opentelemetry 1.x (legacy)
            from splunk_opentelemetry import start as splunk_start_legacy

            splunk_start_legacy()
        except ImportError:
            _logger.warning(
                "ENABLE_SPLUNK_OTEL=true but splunk-opentelemetry is not installed. "
                'Run: pip install "troubleshooting-agent[observability]"'
            )
            return False

    _init_httpx_instrumentation()
    _otel_initialized = True
    _logger.info("Splunk OTel initialized service=%s", settings.otel_service_name)
    return True


# ---------------------------------------------------------------------------
# Auto-instrumentation
# httpx covers outbound LLM HTTP; LangGraph/MCP use manual spans below.
# ---------------------------------------------------------------------------


def _init_httpx_instrumentation() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        _logger.debug("opentelemetry-instrumentation-httpx not installed; LLM HTTP spans skipped")


def otel_active() -> bool:
    return _otel_initialized


# ---------------------------------------------------------------------------
# Manual span helper
# No-op when OTel is off; used for slack.alert, agent.investigation, mcp.tool, etc.
# ---------------------------------------------------------------------------


@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Manual span when Splunk OTel is active; no-op otherwise."""
    if not _otel_initialized:
        yield None
        return

    try:
        from opentelemetry import trace
    except ImportError:
        yield None
        return

    tracer = trace.get_tracer("workshop_shared")
    with tracer.start_as_current_span(name, attributes=attributes or {}) as current:
        yield current
