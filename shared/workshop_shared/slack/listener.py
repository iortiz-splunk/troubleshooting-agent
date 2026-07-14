"""Socket Mode listener: Observability alert in Slack -> agent -> thread reply."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from workshop_shared.agent_registry import run_chat
from workshop_shared.config import Settings
from workshop_shared.observability.logging_trace import (
    log_investigate_failed,
    log_investigate_start,
)
from workshop_shared.observability.otel import span as otel_span
from workshop_shared.slack.channels import resolve_alerts_channel_id
from workshop_shared.slack.messages import (
    extract_message_text,
    format_o11y_alert_context,
    parse_o11y_alert_context,
    skip_reason,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Investigation prompt template
# Filled with parsed O11y fields and the raw alert text before run_chat().
# ---------------------------------------------------------------------------
INVESTIGATION_PROMPT = """An Observability alert was posted to Slack. Investigate it using Splunk
Observability MCP tools (o11y_*). Use the parsed identifiers below when querying alerts, metrics,
and traces. Summarize findings and recommended next steps.

Parsed from alert:
{parsed_context}

Full alert message:
{alert_text}
"""


def _refetch_slack_message(
    client: WebClient,
    *,
    channel_id: str,
    message_ts: str,
) -> dict[str, Any] | None:
    """Load the full message from Slack (Socket Mode events are often incomplete)."""
    try:
        history = client.conversations_history(
            channel=channel_id,
            latest=message_ts,
            inclusive=True,
            limit=1,
        )
    except Exception:
        logger.debug("Could not refetch Slack message ts=%s", message_ts, exc_info=True)
        return None

    messages = history.get("messages", [])
    if messages and isinstance(messages[0], dict):
        return messages[0]
    return None


def _should_refetch_message(event: dict[str, Any]) -> bool:
    """Refetch when the live event may omit attachment/block fields used for filtering."""
    if event.get("subtype") == "bot_message":
        return True
    if not isinstance(event.get("text"), str) or not event.get("text", "").strip():
        return True
    return False


def _enrich_message_event(
    event: dict[str, Any],
    client: WebClient,
    *,
    channel_id: str,
) -> dict[str, Any]:
    message_ts = event.get("ts")
    if not isinstance(message_ts, str) or not _should_refetch_message(event):
        return event
    refetched = _refetch_slack_message(client, channel_id=channel_id, message_ts=message_ts)
    return refetched if refetched is not None else event


def _should_process_alert(event: dict[str, Any], *, our_bot_user_id: str) -> bool:
    """Return True for top-level alert posts (including Splunk integration bot messages)."""
    return skip_reason(event, our_bot_user_id=our_bot_user_id) is None


def _build_investigation_prompt(alert_text: str) -> str:
    context = parse_o11y_alert_context(alert_text)
    return INVESTIGATION_PROMPT.format(
        parsed_context=format_o11y_alert_context(context),
        alert_text=alert_text.strip(),
    )


# ---------------------------------------------------------------------------
# Slack app setup
# Resolves the alerts channel, registers the message handler, and returns the app.
# ---------------------------------------------------------------------------
def create_slack_app(settings: Settings) -> tuple[App, str]:
    """Create Bolt app and resolve alerts channel ID."""
    if not settings.slack_bot_token or not settings.slack_signing_secret:
        msg = "SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET are required"
        raise ValueError(msg)

    client = WebClient(token=settings.slack_bot_token)
    channel_id = resolve_alerts_channel_id(settings, client)
    auth = client.auth_test()
    our_bot_user_id = auth.get("user_id", "")
    if not isinstance(our_bot_user_id, str):
        our_bot_user_id = ""

    app = App(token=settings.slack_bot_token, signing_secret=settings.slack_signing_secret)
    processed: set[str] = set()

    # -----------------------------------------------------------------------
    # Message handler
    # Filters alerts, dedupes by timestamp, runs the agent, replies in-thread.
    # -----------------------------------------------------------------------
    @app.event("message")
    def handle_message(event: dict[str, Any], say: Any, client: WebClient) -> None:
        if event.get("channel") != channel_id:
            return

        message_ts = event.get("ts")
        if not isinstance(message_ts, str):
            return
        if message_ts in processed:
            return

        event = _enrich_message_event(event, client, channel_id=channel_id)
        reason = skip_reason(event, our_bot_user_id=our_bot_user_id)
        if reason:
            logger.info(
                "Skipped message ts=%s subtype=%s: %s",
                message_ts,
                event.get("subtype"),
                reason,
            )
            return

        processed.add(message_ts)

        text = extract_message_text(event)
        if not text.strip():
            return

        logger.info("Processing alert message ts=%s", message_ts)
        alert_context = parse_o11y_alert_context(text)

        if alert_context.get("event_id"):
            logger.info("Parsed O11y event_id=%s", alert_context["event_id"])
        elif alert_context.get("alert_id"):
            logger.info("Parsed O11y alert_id=%s (event_id pending)", alert_context["alert_id"])
        else:
            logger.warning(
                "No O11y event_id in Slack message ts=%s; will resolve via MCP if possible",
                message_ts,
            )

        inv_id = f"slack:{message_ts}"
        try:
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=":mag: Troubleshooting agent is investigating this alert...",
            )
            prompt = _build_investigation_prompt(text)
            with otel_span(
                "slack.alert",
                {
                    "slack.channel": channel_id,
                    "slack.message_ts": message_ts,
                    "o11y.service": alert_context.get("service", ""),
                    "o11y.environment": alert_context.get("environment", ""),
                },
            ):
                log_investigate_start(
                    service=alert_context.get("service"),
                    environment=alert_context.get("environment"),
                )
                response = run_chat(
                    settings,
                    prompt,
                    investigation_id=inv_id,
                    source="slack",
                    investigation_metadata=alert_context,
                )
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=response[:39000],
            )
        except Exception as exc:
            log_investigate_failed(error=str(exc))
            logger.exception("Agent investigation failed for ts=%s", message_ts)
            client.chat_postMessage(
                channel=channel_id,
                thread_ts=message_ts,
                text=":x: Troubleshooting agent failed to investigate this alert. Check logs.",
            )

    return app, channel_id


# ---------------------------------------------------------------------------
# Listener entry points
# Blocking Socket Mode start for CLI; async wrapper for tests or future use.
# ---------------------------------------------------------------------------
def run_slack_listener(settings: Settings) -> None:
    """Start Socket Mode listener (blocking)."""
    if not settings.slack_app_token:
        msg = "SLACK_APP_TOKEN is required for slack-listen (Socket Mode)"
        raise ValueError(msg)

    app, channel_id = create_slack_app(settings)
    logger.info("Listening on channel id=%s", channel_id)
    handler = SocketModeHandler(app, settings.slack_app_token)
    handler.start()  # type: ignore[no-untyped-call]


async def run_slack_listener_async(settings: Settings) -> None:
    """Run Socket Mode listener without blocking the asyncio loop."""
    await asyncio.to_thread(run_slack_listener, settings)
