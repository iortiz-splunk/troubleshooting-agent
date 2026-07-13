"""Brief structured logs for agent investigations (terminal-friendly)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from workshop_shared.config import Settings

# ---------------------------------------------------------------------------
# Redaction and preview helpers
# Safe one-line summaries for terminal logs; secrets stripped from tool args.
# ---------------------------------------------------------------------------

_SENSITIVE_KEYS = frozenset(
    {
        "token",
        "api_key",
        "password",
        "secret",
        "authorization",
        "bearer",
        "x-sf-token",
    }
)

_logger = logging.getLogger("workshop_shared")

# ---------------------------------------------------------------------------
# Per-investigation context (contextvars)
# Propagates investigation_id and counters across async/sync without threading.
# ---------------------------------------------------------------------------

_settings_var: ContextVar[Settings | None] = ContextVar("trace_settings", default=None)
_investigation_id_var: ContextVar[str | None] = ContextVar("investigation_id", default=None)
_metadata_var: ContextVar[dict[str, str] | None] = ContextVar(
    "investigation_metadata", default=None
)
_llm_turn_var: ContextVar[int] = ContextVar("llm_turn", default=0)
_tool_call_count_var: ContextVar[int] = ContextVar("tool_call_count", default=0)
_start_time_var: ContextVar[float | None] = ContextVar("investigation_start", default=None)


def preview(text: str, *, limit: int = 160) -> str:
    """Collapse whitespace and truncate for one-line logs."""
    one_line = " ".join(text.split())
    if len(one_line) <= limit:
        return one_line
    return f"{one_line[: limit - 3]}..."


def preview_params(args: dict[str, Any], *, debug: bool = False) -> str:
    """JSON-safe tool-arg summary with secrets redacted."""
    redacted = _redact_dict(args)
    raw = json.dumps(redacted, default=str, separators=(",", ":"))
    if debug:
        return preview(raw, limit=500)
    return preview(raw, limit=120)


def _redact_dict(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(s in key_lower for s in _SENSITIVE_KEYS):
                out[key] = "<redacted>"
            else:
                out[key] = _redact_dict(item)
        return out
    if isinstance(value, list):
        return [_redact_dict(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Log prefix (investigation ID + optional OTel trace_id)
# ---------------------------------------------------------------------------


def _trace_ids_suffix() -> str:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            return f" trace_id={format(ctx.trace_id, '032x')}"
    except Exception:
        pass
    return ""


def _prefix() -> str:
    inv = _investigation_id_var.get()
    inv_part = f"[inv={inv}] " if inv else ""
    return f"{inv_part}{_trace_ids_suffix()}".rstrip()


def _log(level: int, message: str, *args: Any) -> None:
    settings = _settings_var.get()
    if settings is not None and not settings.agent_log_trace:
        return
    prefix = _prefix()
    text = message % args if args else message
    if prefix:
        _logger.log(level, "%s %s", prefix, text)
    else:
        _logger.log(level, "%s", text)


# ---------------------------------------------------------------------------
# Logging setup
# Called from CLI when AGENT_LOG_TRACE or --trace is enabled.
# ---------------------------------------------------------------------------


def setup_logging(settings: Settings) -> None:
    """Configure root logging for agent trace output."""
    if settings.log_format == "json":
        logging.basicConfig(
            level=logging.INFO,
            format='{"level":"%(levelname)s","message":"%(message)s"}',
        )
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("workshop_shared").setLevel(logging.INFO)


def trace_enabled() -> bool:
    settings = _settings_var.get()
    return settings is None or settings.agent_log_trace


# ---------------------------------------------------------------------------
# Investigation scope context manager
# Bind/unbind contextvars for one chat or Slack investigation.
# ---------------------------------------------------------------------------


@contextmanager
def investigation_scope(
    settings: Settings,
    investigation_id: str,
    *,
    metadata: dict[str, str] | None = None,
) -> Iterator[None]:
    """Bind investigation context for correlated logs across async/sync calls."""
    tok_settings = _settings_var.set(settings)
    tok_inv = _investigation_id_var.set(investigation_id)
    tok_meta = _metadata_var.set(metadata)
    tok_turn = _llm_turn_var.set(0)
    tok_tools = _tool_call_count_var.set(0)
    tok_start = _start_time_var.set(time.monotonic())
    try:
        yield
    finally:
        _start_time_var.reset(tok_start)
        _tool_call_count_var.reset(tok_tools)
        _llm_turn_var.reset(tok_turn)
        _metadata_var.reset(tok_meta)
        _investigation_id_var.reset(tok_inv)
        _settings_var.reset(tok_settings)


def new_chat_investigation_id() -> str:
    return f"chat:{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Structured log events
# One-line INFO logs for agent lifecycle, LLM turns, and MCP tool calls.
# ---------------------------------------------------------------------------


def log_agent_start(*, provider: str, mcp_tool_count: int) -> None:
    _log(logging.INFO, "agent start provider=%s mcp_tools=%d", provider, mcp_tool_count)


def log_investigate_start(
    *,
    service: str | None,
    environment: str | None,
    mcp_tools: int | None = None,
) -> None:
    parts: list[str] = ["investigate"]
    if service:
        parts.append(f"service={service}")
    if environment:
        parts.append(f"env={environment}")
    if mcp_tools is not None:
        parts.append(f"mcp_tools={mcp_tools}")
    _log(logging.INFO, " ".join(parts))


def log_llm_turn(*, tool_names: list[str] | None, final_chars: int | None) -> None:
    turn = _llm_turn_var.get() + 1
    _llm_turn_var.set(turn)
    if tool_names:
        _log(logging.INFO, "llm turn=%d tools=%s", turn, ",".join(tool_names))
    elif final_chars is not None:
        _log(logging.INFO, "llm turn=%d final chars=%d", turn, final_chars)


def log_mcp_call(*, tool_name: str, arguments: dict[str, Any], result: str) -> None:
    settings = _settings_var.get()
    debug = settings.agent_log_debug if settings else False
    count = _tool_call_count_var.get() + 1
    _tool_call_count_var.set(count)

    arg_preview = preview_params(arguments, debug=debug)
    _log(logging.INFO, "mcp %s args=%s", tool_name, arg_preview)

    is_error = result.lstrip().startswith("ERROR:")
    if is_error:
        err_line = preview(result.replace("ERROR:", "", 1).strip(), limit=160)
        _log(logging.INFO, "mcp %s ERROR %s", tool_name, err_line)
    else:
        _log(logging.INFO, "mcp %s ok bytes=%d", tool_name, len(result.encode("utf-8")))


def log_agent_done(*, message_count: int) -> None:
    start = _start_time_var.get()
    duration_ms = int((time.monotonic() - start) * 1000) if start else 0
    turns = _llm_turn_var.get()
    tool_calls = _tool_call_count_var.get()
    _log(
        logging.INFO,
        "done turns=%d tool_calls=%d messages=%d duration_ms=%d",
        turns,
        tool_calls,
        message_count,
        duration_ms,
    )


def log_investigate_done() -> None:
    log_agent_done(message_count=0)


def log_investigate_failed(*, error: str) -> None:
    _log(logging.ERROR, "investigate failed %s", preview(error, limit=160))
