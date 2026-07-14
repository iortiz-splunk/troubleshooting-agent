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
from workshop_shared.observability.investigation_log import (
    alert_identifiers,
    close_investigation_log,
    current_investigation_log_path,
    metadata_identifiers,
    open_investigation_log,
    summarize_mcp_alerts,
    write_investigation_log,
)

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
_step_var: ContextVar[int] = ContextVar("log_step", default=0)
_start_time_var: ContextVar[float | None] = ContextVar("investigation_start", default=None)

_LINE = "─" * 62
_HEADER = "═" * 62


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


def _human_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    return f"{size / 1024:.1f} KB"


def _next_step() -> int:
    step = _step_var.get() + 1
    _step_var.set(step)
    return step


def _emit(lines: list[str], *, level: int = logging.INFO) -> None:
    """Write human-oriented lines to the console when trace is enabled."""
    if not trace_enabled():
        return
    for line in lines:
        prefix = _prefix()
        if prefix:
            _logger.log(level, "%s %s", prefix, line)
        else:
            _logger.log(level, "%s", line)


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
    tok_step = _step_var.set(0)
    tok_start = _start_time_var.set(time.monotonic())
    log_path = open_investigation_log(settings, investigation_id, metadata=metadata)
    if log_path is not None and trace_enabled():
        _emit([f"Log file: {log_path}"])
    try:
        yield
    finally:
        start = _start_time_var.get()
        duration_ms = int((time.monotonic() - start) * 1000) if start else 0
        close_investigation_log(
            duration_ms=duration_ms,
            llm_turns=_llm_turn_var.get(),
            tool_calls=_tool_call_count_var.get(),
        )
        _start_time_var.reset(tok_start)
        _step_var.reset(tok_step)
        _tool_call_count_var.reset(tok_tools)
        _llm_turn_var.reset(tok_turn)
        _metadata_var.reset(tok_meta)
        _investigation_id_var.reset(tok_inv)
        _settings_var.reset(tok_settings)


def new_chat_investigation_id() -> str:
    return f"chat:{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Structured log events
# Human-readable console lines + JSONL file records for all workshop parts.
# ---------------------------------------------------------------------------
def log_investigation_banner(
    *,
    workshop_part: str,
    source: str,
    query: str,
    provider: str,
    mcp_tool_count: int,
    skill: str | None = None,
    graph: str | None = None,
    service: str | None = None,
    environment: str | None = None,
) -> None:
    """Open a readable investigation header in the terminal and log file."""
    inv_id = _investigation_id_var.get() or "unknown"
    write_investigation_log(
        "investigation_banner",
        workshop_part=workshop_part,
        source=source,
        query_preview=preview(query, limit=240),
        provider=provider,
        mcp_tool_count=mcp_tool_count,
        skill=skill,
        graph=graph,
        service=service,
        environment=environment,
    )

    lines = [
        "",
        _HEADER,
        f" Investigation  {inv_id}  |  {workshop_part}  |  {source}",
        _LINE,
        f" Query: {preview(query, limit=240)}",
    ]
    if service:
        lines.append(f" Service: {service}" + (f" ({environment})" if environment else ""))
    if skill:
        lines.append(f" Skill: {skill}")
    if graph:
        lines.append(f" Workflow: {graph}")
    lines.append(f" LLM: {provider}  |  MCP tools available: {mcp_tool_count}")
    lines.append(_HEADER)
    _emit(lines)


def log_agent_start(*, provider: str, mcp_tool_count: int) -> None:
    write_investigation_log(
        "agent_start",
        provider=provider,
        mcp_tool_count=mcp_tool_count,
    )


def log_skill_injected(*, skill_name: str) -> None:
    step = _next_step()
    _log(logging.INFO, "[%d] Skill loaded: %s", step, skill_name)
    write_investigation_log("skill_injected", skill_name=skill_name, step=step)


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
    step = _next_step()
    if tool_names:
        tools = ", ".join(tool_names)
        _log(logging.INFO, "[%d] LLM turn %d — calling tools: %s", step, turn, tools)
        write_investigation_log("llm_turn", turn=turn, step=step, tool_names=tool_names)
    elif final_chars is not None:
        _log(
            logging.INFO,
            "[%d] LLM turn %d — composing final response (%d chars)",
            step,
            turn,
            final_chars,
        )
        write_investigation_log("llm_turn", turn=turn, step=step, final_chars=final_chars)


def log_mcp_call(*, tool_name: str, arguments: dict[str, Any], result: str) -> None:
    settings = _settings_var.get()
    debug = settings.agent_log_debug if settings else False
    count = _tool_call_count_var.get() + 1
    _tool_call_count_var.set(count)
    step = _next_step()

    arg_preview = preview_params(arguments, debug=debug)
    file_record: dict[str, Any] = {
        "tool_name": tool_name,
        "arguments": _redact_dict(arguments),
        "result_bytes": len(result.encode("utf-8")),
        "step": step,
        "tool_call": count,
    }
    alerts_returned: list[dict[str, str]] = []
    if tool_name == "o11y_search_alerts_or_incidents":
        alerts_returned = summarize_mcp_alerts(result)
        file_record["alerts_returned"] = alerts_returned

    is_error = result.lstrip().startswith("ERROR:")
    if is_error:
        err_line = preview(result.replace("ERROR:", "", 1).strip(), limit=160)
        _log(logging.INFO, "[%d] MCP %s — ERROR: %s", step, tool_name, err_line)
        _log(logging.INFO, "     args: %s", arg_preview)
        file_record["error"] = err_line
    else:
        size = len(result.encode("utf-8"))
        extra = ""
        if alerts_returned:
            extra = f" | alerts={len(alerts_returned)}"
        _log(
            logging.INFO,
            "[%d] MCP %s — OK (%s)%s",
            step,
            tool_name,
            _human_bytes(size),
            extra,
        )
        if debug:
            _log(logging.INFO, "     args: %s", arg_preview)

    write_investigation_log("mcp_call", **file_record)


def log_agent_done(*, message_count: int) -> None:
    start = _start_time_var.get()
    duration_ms = int((time.monotonic() - start) * 1000) if start else 0
    turns = _llm_turn_var.get()
    tool_calls = _tool_call_count_var.get()
    write_investigation_log(
        "agent_done",
        message_count=message_count,
        duration_ms=duration_ms,
        llm_turns=turns,
        tool_calls=tool_calls,
    )
    log_path = current_investigation_log_path()
    lines = [
        _LINE,
        f" Done — {turns} LLM turns | {tool_calls} tool calls | {duration_ms / 1000:.1f}s",
    ]
    if log_path is not None:
        lines.append(f" Log file: {log_path}")
    lines.append(_HEADER)
    _emit(lines)


def log_agent_response(text: str) -> None:
    """Print the final agent answer in the console and persist it to the JSONL log."""
    body = text.strip() or "(empty response)"
    write_investigation_log(
        "agent_response",
        chars=len(body),
        preview=preview(body, limit=400),
        body=body,
    )
    lines = [
        "",
        _LINE,
        " Agent response",
        _LINE,
        *body.splitlines(),
        _HEADER,
    ]
    _emit(lines)


def log_node_enter(*, node: str, **fields: str | None) -> None:
    extras = " ".join(f"{key}={value}" for key, value in fields.items() if value)
    step = _next_step()
    label = f"Graph ▸ {node} (start)"
    if extras:
        label = f"{label} {extras}"
    _log(logging.INFO, "[%d] %s", step, label)
    write_investigation_log(
        "node_enter",
        node=node,
        step=step,
        **{k: v for k, v in fields.items() if v},
    )


def log_node_exit(*, node: str, **fields: str | None) -> None:
    extras = " ".join(f"{key}={value}" for key, value in fields.items() if value)
    step = _next_step()
    label = f"Graph ▸ {node} (done)"
    if extras:
        label = f"{label} {extras}"
    _log(logging.INFO, "[%d] %s", step, label)
    write_investigation_log(
        "node_exit",
        node=node,
        step=step,
        **{k: v for k, v in fields.items() if v},
    )


def log_node_snapshot(
    *,
    node: str,
    phase: str,
    investigation_metadata: dict[str, str] | None = None,
    alert_payload: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    """Write alert IDs and metadata at a workflow step for cross-node comparison."""
    write_investigation_log(
        "node_snapshot",
        node=node,
        phase=phase,
        slack_metadata=metadata_identifiers(investigation_metadata),
        alert=alert_identifiers(alert_payload),
        **extra,
    )


def log_investigate_done() -> None:
    log_agent_done(message_count=0)


def log_investigate_failed(*, error: str) -> None:
    _log(logging.ERROR, "investigate failed %s", preview(error, limit=160))
