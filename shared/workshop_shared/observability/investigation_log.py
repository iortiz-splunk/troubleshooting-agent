"""Per-investigation JSONL trace files for debugging agent workflow."""

from __future__ import annotations

import json
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workshop_shared.config import Settings

_log_path_var: ContextVar[Path | None] = ContextVar("investigation_log_path", default=None)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_filename(investigation_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", investigation_id).strip("-")
    return safe or "investigation"


# ---------------------------------------------------------------------------
# Alert identifier helpers
# Extract O11y IDs for cross-node comparison in log files.
# ---------------------------------------------------------------------------
def alert_identifiers(alert: dict[str, Any] | None) -> dict[str, str]:
    """Return key O11y identifiers from an MCP alert record."""
    if not alert:
        return {}
    ids: dict[str, str] = {}
    mapping = {
        "event_id": ("eventId", "event_id"),
        "incident_id": ("incidentId",),
        "alert_id": ("id",),
        "detector_id": ("detectorId",),
        "detector": ("detector", "detectLabel"),
    }
    for out_key, in_keys in mapping.items():
        for key in in_keys:
            value = alert.get(key)
            if isinstance(value, str) and value.strip():
                ids[out_key] = value.strip()
                break
    props = alert.get("customProperties")
    if isinstance(props, dict):
        for key in ("sf_service", "sf_environment"):
            value = props.get(key)
            if isinstance(value, str) and value.strip():
                ids[key] = value.strip()
    return ids


def metadata_identifiers(metadata: dict[str, str] | None) -> dict[str, str]:
    if not metadata:
        return {}
    keys = (
        "event_id",
        "incident_id",
        "alert_id",
        "detector_id",
        "detector",
        "rule",
        "service",
        "environment",
    )
    return {key: metadata[key] for key in keys if metadata.get(key)}


def summarize_mcp_alerts(result: str, *, limit: int = 5) -> list[dict[str, str]]:
    """Parse alert search JSON and return identifier summaries for the top rows."""
    try:
        payload = json.loads(result)
    except json.JSONDecodeError:
        return []
    alerts = payload.get("alerts") if isinstance(payload, dict) else None
    if not isinstance(alerts, list):
        return []
    summaries: list[dict[str, str]] = []
    for alert in alerts[:limit]:
        if isinstance(alert, dict):
            row = alert_identifiers(alert)
            if row:
                summaries.append(row)
    return summaries


# ---------------------------------------------------------------------------
# File lifecycle
# One JSONL file per investigation under agent_log_dir (default: shared/logs/investigations).
# ---------------------------------------------------------------------------
def open_investigation_log(
    settings: Settings,
    investigation_id: str,
    *,
    metadata: dict[str, str] | None = None,
) -> Path | None:
    """Create the investigation log file and write the opening record."""
    log_dir = (settings.agent_log_dir or "").strip()
    if not log_dir:
        return None

    root = Path(log_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{_safe_filename(investigation_id)}.jsonl"
    _log_path_var.set(path)

    write_investigation_log(
        "investigation_start",
        investigation_id=investigation_id,
        metadata=metadata_identifiers(metadata),
    )
    return path


def close_investigation_log(**fields: Any) -> None:
    """Write the closing record for the current investigation log."""
    write_investigation_log("investigation_done", **fields)
    _log_path_var.set(None)


def current_investigation_log_path() -> Path | None:
    return _log_path_var.get()


def write_investigation_log(event: str, **fields: Any) -> None:
    """Append one JSON line to the active investigation log file."""
    path = _log_path_var.get()
    if path is None:
        return

    record: dict[str, Any] = {
        "ts": _utc_now(),
        "event": event,
    }
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, str, int, float, bool)):
            record[key] = value
        else:
            record[key] = str(value)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
