"""Galileo Cloud callbacks for LangGraph agent traces."""

from __future__ import annotations

import logging
import os
from typing import Any

from troubleshooting_agent.config import Settings

_logger = logging.getLogger("troubleshooting_agent")


def _apply_galileo_env(settings: Settings) -> None:
    if settings.galileo_api_key:
        os.environ.setdefault("GALILEO_API_KEY", settings.galileo_api_key)
    os.environ.setdefault("GALILEO_PROJECT", settings.galileo_project)
    os.environ.setdefault("GALILEO_LOG_STREAM", settings.galileo_log_stream)
    if settings.galileo_console_url:
        os.environ.setdefault("GALILEO_CONSOLE_URL", settings.galileo_console_url)


def build_galileo_callback(settings: Settings) -> Any | None:
    """Return GalileoAsyncCallback when Galileo is enabled and configured."""
    if not settings.enable_galileo:
        return None
    if not settings.galileo_api_key:
        _logger.warning("ENABLE_GALILEO=true but GALILEO_API_KEY is not set")
        return None

    _apply_galileo_env(settings)

    try:
        from galileo.handlers.langchain import GalileoAsyncCallback
    except ImportError:
        _logger.warning(
            "ENABLE_GALILEO=true but galileo is not installed. "
            'Run: pip install "troubleshooting-agent[observability]"'
        )
        return None

    _logger.info(
        "Galileo enabled project=%s stream=%s",
        settings.galileo_project,
        settings.galileo_log_stream,
    )
    return GalileoAsyncCallback()
