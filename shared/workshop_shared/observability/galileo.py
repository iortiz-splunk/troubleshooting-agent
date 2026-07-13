"""Galileo Cloud callbacks for LangGraph agent traces."""

from __future__ import annotations

import logging
import os
from typing import Any

from workshop_shared.config import Settings

_logger = logging.getLogger("workshop_shared")

# ---------------------------------------------------------------------------
# Environment wiring
# Galileo SDK reads GALILEO_* from os.environ; copy from Settings when set.
# ---------------------------------------------------------------------------


def _apply_galileo_env(settings: Settings) -> None:
    if settings.galileo_api_key:
        os.environ.setdefault("GALILEO_API_KEY", settings.galileo_api_key)
    os.environ.setdefault("GALILEO_PROJECT", settings.galileo_project)
    os.environ.setdefault("GALILEO_LOG_STREAM", settings.galileo_log_stream)
    # Required when Galileo is enabled — tenant-specific; no SDK default assumed.
    if settings.galileo_console_url:
        os.environ.setdefault("GALILEO_CONSOLE_URL", settings.galileo_console_url)


# ---------------------------------------------------------------------------
# Session naming
# Build a human-readable Galileo session name from investigation metadata.
# ---------------------------------------------------------------------------


def build_galileo_session_name(
    investigation_id: str,
    investigation_metadata: dict[str, str] | None,
) -> str:
    """Return a session name keyed by O11y eventId so alerts are easy to find in the UI."""
    meta = investigation_metadata or {}
    # eventId matches the alert event in O11y Cloud; fall back to incident/alert/rule.
    session_key = (
        meta.get("event_id")
        or meta.get("incident_id")
        or meta.get("alert_id")
        or meta.get("rule")
    )

    if session_key:
        parts = [f"slack-alert-{session_key}"]
        if service := meta.get("service"):
            parts.append(service)
        return " | ".join(parts)

    if investigation_id.startswith("chat:"):
        return f"chat-{investigation_id.removeprefix('chat:')}"
    return investigation_id


# ---------------------------------------------------------------------------
# Callback factory
# Returns GalileoAsyncCallback with a named session for each investigation.
# ---------------------------------------------------------------------------


def build_galileo_callback(
    settings: Settings,
    *,
    investigation_id: str,
    investigation_metadata: dict[str, str] | None = None,
) -> Any | None:
    """Return GalileoAsyncCallback when Galileo is enabled and configured."""
    if not settings.enable_galileo:
        return None
    if not settings.galileo_api_key:
        _logger.warning("ENABLE_GALILEO=true but GALILEO_API_KEY is not set")
        return None
    if not settings.galileo_console_url:
        _logger.warning("ENABLE_GALILEO=true but GALILEO_CONSOLE_URL is not set")
        return None

    _apply_galileo_env(settings)

    try:
        from galileo import GalileoLogger
        from galileo.handlers.langchain import GalileoAsyncCallback
    except ImportError:
        _logger.warning(
            "ENABLE_GALILEO=true but galileo is not installed. "
            'Run: pip install "troubleshooting-agent[observability]"'
        )
        return None

    session_name = build_galileo_session_name(investigation_id, investigation_metadata)
    logger = GalileoLogger(
        project=settings.galileo_project,
        log_stream=settings.galileo_log_stream,
    )
    external_id = investigation_id
    if investigation_metadata:
        external_id = (
            investigation_metadata.get("event_id")
            or investigation_metadata.get("incident_id")
            or investigation_metadata.get("alert_id")
            or investigation_id
        )
    session_kwargs: dict[str, Any] = {
        "name": session_name,
        "external_id": external_id,
    }
    if investigation_metadata:
        session_kwargs["metadata"] = dict(investigation_metadata)
    logger.start_session(**session_kwargs)

    _logger.info(
        "Galileo session=%s project=%s stream=%s console=%s",
        session_name,
        settings.galileo_project,
        settings.galileo_log_stream,
        settings.galileo_console_url,
    )
    return GalileoAsyncCallback(galileo_logger=logger)
