"""Extract readable text from Slack message events."""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# O11y alert parsing regexes
# Match sf_service, sf_environment, rule name, and severity from Slack text.
# ---------------------------------------------------------------------------

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
_O11Y_RULE_RESOLVED_RE = re.compile(
    r'Rule\s+"[^"]+"\s+(?:was\s+)?(?:resolved|cleared|stopped)\b',
    re.IGNORECASE,
)
_O11Y_RESOLVED_HEADER_RE = re.compile(
    r"(?:splunk\s+observability\s+)?"
    r"(?:ok|clear(?:ed)?|resolved|recovered|stopped|manually\s*resolved)\s+alert\s*:",
    re.IGNORECASE,
)
_O11Y_INCIDENT_URL_RE = re.compile(r"/incident/([A-Za-z0-9_-]+)", re.IGNORECASE)
_O11Y_ALERT_URL_RE = re.compile(
    r"(?:alert-details|#/alert|#/event)/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_O11Y_ALERT_DETAILS_URL_RE = re.compile(
    r"alert-details/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_O11Y_INCIDENT_ID_LABEL_RE = re.compile(
    r"(?:incident[_\s-]?id|incidentId)\s*[:=]\s*([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_O11Y_EVENT_ID_LABEL_RE = re.compile(
    r"(?:event[_\s-]?id|eventId)\s*[:=]\s*([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_O11Y_EVENT_ID_URL_RE = re.compile(
    r"[?&#]eventId=([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_O11Y_ALERT_ID_LABEL_RE = re.compile(
    r"(?:alert[_\s-]?id|alertId)\s*[:=]\s*([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_MRKDWN_URL_RE = re.compile(r"<(https?://[^>|]+)(?:\|[^>]+)?>", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Slack Block Kit text extraction
# Splunk alerts often use blocks/attachments instead of plain event["text"].
# ---------------------------------------------------------------------------


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
            parts.append(element["url"].strip())
        elif element_type == "emoji" and isinstance(element.get("name"), str):
            parts.append(f":{element['name']}:")
    return [part for part in parts if part]


def _block_text(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    if block_type in {"section", "header", "context"}:
        text_value = _rich_text_value(block.get("text"))
        accessory = block.get("accessory")
        if isinstance(accessory, dict):
            accessory_url = accessory.get("url")
            if isinstance(accessory_url, str) and accessory_url.strip():
                return f"{text_value}\n{accessory_url.strip()}".strip()
        return text_value
    if block_type == "rich_text":
        return " ".join(_rich_text_block_elements(block.get("elements")))
    return ""


def _urls_from_mrkdwn(text: str) -> list[str]:
    return [match.group(1).strip() for match in _MRKDWN_URL_RE.finditer(text)]


def _collect_url_fields(obj: Any) -> list[str]:
    """Walk the Slack event JSON and collect url/title_link fields."""
    urls: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"url", "title_link"} and isinstance(value, str) and value.strip():
                urls.append(value.strip())
            else:
                urls.extend(_collect_url_fields(value))
    elif isinstance(obj, list):
        for item in obj:
            urls.extend(_collect_url_fields(item))
    return urls


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
        title_link = attachment.get("title_link")
        if isinstance(title_link, str) and title_link.strip():
            parts.append(title_link.strip())
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

    for url in _collect_url_fields(event):
        parts.append(url)

    for part in list(parts):
        parts.extend(_urls_from_mrkdwn(part))

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            unique.append(part)
    return "\n".join(unique)


# ---------------------------------------------------------------------------
# Resolved / cleared alert detection
# Skip investigations when Splunk posts "Stopped", "Resolved", "Cleared", etc.
# ---------------------------------------------------------------------------

_O11Y_RESOLVED_LINE_PREFIXES = (
    "stopped:",
    "resolved:",
    "cleared:",
    "recovered:",
    "ok:",
)
_O11Y_RESOLVED_STATUS_TYPES = frozenset(
    {
        "ok",
        "clear",
        "cleared",
        "resolved",
        "recovered",
        "stopped",
        "manuallyresolved",
        "manually_resolved",
    }
)
_O11Y_RESOLVED_LINE_PATTERNS = (
    re.compile(r"^splunk observability\s+ok\s+alert:", re.IGNORECASE),
    re.compile(r"^splunk observability\s+clear(?:ed)?\s+alert:", re.IGNORECASE),
    re.compile(r"^splunk observability\s+resolved\s+alert:", re.IGNORECASE),
    re.compile(r"^splunk observability\s+recovered\s+alert:", re.IGNORECASE),
    re.compile(r"^splunk observability\s+stopped\s+alert:", re.IGNORECASE),
    re.compile(r"^splunk observability\s+manually\s*resolved\s+alert:", re.IGNORECASE),
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
    " manually resolved",
    " manuallyresolved",
    " status: ok",
    " statusextended: ok",
)


def _strip_slack_mrkdwn(line: str) -> str:
    """Remove common Slack mrkdwn wrappers so prefix checks work on block text."""
    stripped = line.strip()
    while stripped and stripped[0] in "*_~`":
        stripped = stripped[1:]
    while stripped and stripped[-1] in "*_~`":
        stripped = stripped[:-1]
    return stripped.strip()


def _o11y_resolved_status_from_header(text: str) -> bool:
    """True when Splunk header severity is a cleared/resolved status (not Minor/Major/etc.)."""
    match = _O11Y_SEVERITY_RE.search(text)
    if not match:
        return False
    status = match.group(1).strip().lower().replace("-", "_")
    return status in _O11Y_RESOLVED_STATUS_TYPES


def is_o11y_resolved_alert(text: str) -> bool:
    """True for Splunk Observability cleared/stopped/resolved Slack notifications."""
    normalized = text.strip()
    if not normalized:
        return False

    if _o11y_resolved_status_from_header(normalized):
        return True
    if _O11Y_RULE_RESOLVED_RE.search(normalized):
        return True

    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        plain = _strip_slack_mrkdwn(stripped)
        lower = plain.lower()
        if lower.startswith(_O11Y_RESOLVED_LINE_PREFIXES):
            return True
        if any(pattern.match(plain) for pattern in _O11Y_RESOLVED_LINE_PATTERNS):
            return True
        if _O11Y_RESOLVED_HEADER_RE.search(plain):
            return True

    lower_text = normalized.lower()
    return any(phrase in lower_text for phrase in _O11Y_RESOLVED_PHRASES)


def is_o11y_stopped_alert(text: str) -> bool:
    """Backward-compatible alias for resolved-alert detection."""
    return is_o11y_resolved_alert(text)


# ---------------------------------------------------------------------------
# Alert context for the agent prompt
# Parse structured fields and format them for the investigation template.
# ---------------------------------------------------------------------------


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

    incident_label = _O11Y_INCIDENT_ID_LABEL_RE.search(text)
    if incident_label:
        context["incident_id"] = incident_label.group(1).strip()
    else:
        incident_url = _O11Y_INCIDENT_URL_RE.search(text)
        if incident_url:
            context["incident_id"] = incident_url.group(1).strip()

    alert_details = _O11Y_ALERT_DETAILS_URL_RE.search(text)
    if alert_details:
        context["alert_id"] = alert_details.group(1).strip()
    else:
        alert_url = _O11Y_ALERT_URL_RE.search(text)
        if alert_url:
            context["alert_id"] = alert_url.group(1).strip()

    alert_label = _O11Y_ALERT_ID_LABEL_RE.search(text)
    if alert_label and "alert_id" not in context:
        context["alert_id"] = alert_label.group(1).strip()

    event_label = _O11Y_EVENT_ID_LABEL_RE.search(text)
    if event_label:
        context["event_id"] = event_label.group(1).strip()
    else:
        event_url = _O11Y_EVENT_ID_URL_RE.search(text)
        if event_url:
            context["event_id"] = event_url.group(1).strip()

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
        "alert_id": "Alert ID (O11y UI)",
        "event_id": "Event ID (O11y)",
        "incident_id": "Incident ID",
    }
    return "\n".join(f"- {labels.get(key, key)}: {value}" for key, value in context.items())


# ---------------------------------------------------------------------------
# Message filter
# Returns a skip reason string, or None if the listener should investigate.
# ---------------------------------------------------------------------------


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
