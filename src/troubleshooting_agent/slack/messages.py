"""Extract readable text from Slack message events."""

from __future__ import annotations

import re
from typing import Any

_O11Y_SIGNAL_PAIR_RE = re.compile(
    r"\{sf_environment=([^,}]+),\s*sf_service=([^}]+)\}",
    re.IGNORECASE,
)
_O11Y_ENV_RE = re.compile(r"sf_environment=([^,}\s]+)", re.IGNORECASE)
_O11Y_SERVICE_RE = re.compile(r"sf_service=([^,}\s]+)", re.IGNORECASE)
_O11Y_RULE_TRIGGERED_RE = re.compile(r'Rule "([^"]+)" triggered', re.IGNORECASE)
_O11Y_SEVERITY_RE = re.compile(
    r"Splunk Observability\s+(\w+)\s+Alert:\s*(\S+)",
    re.IGNORECASE,
)


def _rich_text_value(obj: Any) -> str:
    if isinstance(obj, str):
        return obj.strip()
    if not isinstance(obj, dict):
        return ""
    text = obj.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return ""


def _rich_text_block_elements(elements: Any) -> list[str]:
    parts: list[str] = []
    if not isinstance(elements, list):
        return parts
    for element in elements:
        if not isinstance(element, dict):
            continue
        element_type = element.get("type")
        if element_type == "text" and isinstance(element.get("text"), str):
            parts.append(element["text"].strip())
        elif element_type in {"rich_text_section", "rich_text_preformatted", "rich_text_quote"}:
            parts.extend(_rich_text_block_elements(element.get("elements")))
        elif element_type == "rich_text_list":
            for item in element.get("elements") or []:
                if isinstance(item, dict):
                    parts.extend(_rich_text_block_elements(item.get("elements")))
        elif element_type == "link" and isinstance(element.get("url"), str):
            label = element.get("text") or element["url"]
            parts.append(str(label).strip())
        elif element_type == "emoji" and isinstance(element.get("name"), str):
            parts.append(f":{element['name']}:")
    return [part for part in parts if part]


def _block_text(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    if block_type in {"section", "header", "context"}:
        return _rich_text_value(block.get("text"))
    if block_type == "rich_text":
        return " ".join(_rich_text_block_elements(block.get("elements")))
    return ""


def extract_message_text(event: dict[str, Any]) -> str:
    """Combine text, attachment fields, and blocks into one alert body."""
    parts: list[str] = []

    text = event.get("text")
    if isinstance(text, str) and text.strip():
        parts.append(text.strip())

    for attachment in event.get("attachments") or []:
        if not isinstance(attachment, dict):
            continue
        for key in ("pretext", "title", "text", "fallback"):
            value = attachment.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        for field in attachment.get("fields") or []:
            if not isinstance(field, dict):
                continue
            title = field.get("title", "")
            value = field.get("value", "")
            if isinstance(title, str) and isinstance(value, str) and (title or value):
                parts.append(f"{title}: {value}".strip(": "))

    for block in event.get("blocks") or []:
        if isinstance(block, dict):
            block_text = _block_text(block)
            if block_text:
                parts.append(block_text)

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            unique.append(part)
    return "\n".join(unique)


# Splunk Observability Cloud Slack notifications for cleared/resolved incidents.
_O11Y_RESOLVED_LINE_PREFIXES = (
    "stopped:",
    "resolved:",
    "cleared:",
    "recovered:",
    "ok:",
)
_O11Y_RESOLVED_LINE_PATTERNS = (
    re.compile(r"^splunk observability\s+ok\s+alert:", re.IGNORECASE),
    re.compile(r"^splunk observability\s+clear(?:ed)?\s+alert:", re.IGNORECASE),
)
_O11Y_RESOLVED_PHRASES = (
    " was stopped at ",
    " was resolved at ",
    " was cleared at ",
    " has been resolved",
    " has been cleared",
    " has cleared",
    " alert cleared",
    " alert resolved",
    " no longer firing",
    " back to normal",
    " condition cleared",
    " incident resolved",
)


def is_o11y_resolved_alert(text: str) -> bool:
    """True for Splunk Observability cleared/stopped/resolved Slack notifications."""
    normalized = text.strip()
    if not normalized:
        return False

    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith(_O11Y_RESOLVED_LINE_PREFIXES):
            return True
        if any(pattern.match(stripped) for pattern in _O11Y_RESOLVED_LINE_PATTERNS):
            return True

    lower_text = normalized.lower()
    return any(phrase in lower_text for phrase in _O11Y_RESOLVED_PHRASES)


def is_o11y_stopped_alert(text: str) -> bool:
    """Backward-compatible alias for resolved-alert detection."""
    return is_o11y_resolved_alert(text)


def parse_o11y_alert_context(text: str) -> dict[str, str]:
    """Extract service, environment, and rule from Splunk Observability Slack alerts."""
    context: dict[str, str] = {}

    pair = _O11Y_SIGNAL_PAIR_RE.search(text)
    if pair:
        context["environment"] = pair.group(1).strip()
        context["service"] = pair.group(2).strip()
    else:
        env = _O11Y_ENV_RE.search(text)
        if env:
            context["environment"] = env.group(1).strip()
        service = _O11Y_SERVICE_RE.search(text)
        if service:
            context["service"] = service.group(1).strip()

    rule = _O11Y_RULE_TRIGGERED_RE.search(text)
    if rule:
        context["rule"] = rule.group(1).strip()

    severity = _O11Y_SEVERITY_RE.search(text)
    if severity:
        context["severity"] = severity.group(1).strip()
        context["detector"] = severity.group(2).strip()

    return context


def format_o11y_alert_context(context: dict[str, str]) -> str:
    """Human-readable lines for the investigation prompt."""
    if not context:
        return "(extract service and environment from the alert text below)"
    labels = {
        "service": "Service (sf_service)",
        "environment": "Environment (sf_environment)",
        "rule": "Triggered rule",
        "severity": "Severity",
        "detector": "Detector",
    }
    return "\n".join(f"- {labels.get(key, key)}: {value}" for key, value in context.items())


def skip_reason(event: dict[str, Any], *, our_bot_user_id: str) -> str | None:
    """Return why an event was ignored, or None if it should be processed."""
    subtype = event.get("subtype")
    if subtype in {"message_changed", "message_deleted"}:
        return f"subtype={subtype}"
    if event.get("user") == our_bot_user_id:
        return "own_bot_message"
    thread_ts = event.get("thread_ts")
    ts = event.get("ts")
    if thread_ts and ts and thread_ts != ts:
        return "thread_reply"
    text = extract_message_text(event)
    if not text.strip():
        return "no_extractable_text"
    if is_o11y_resolved_alert(text):
        return "o11y_resolved_alert"
    return None
