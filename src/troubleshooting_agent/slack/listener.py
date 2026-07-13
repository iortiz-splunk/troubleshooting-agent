"""Socket Mode listener: Observability alert in Slack -> agent -> thread reply."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from troubleshooting_agent.agent.runner import run_chat
from troubleshooting_agent.config import Settings
from troubleshooting_agent.observability.logging_trace import (
    log_investigate_failed,
    log_investigate_start,
)
from troubleshooting_agent.observability.otel import span as otel_span
from troubleshooting_agent.slack.channels import resolve_alerts_channel_id
from troubleshooting_agent.slack.messages import (
    extract_message_text,
    format_o11y_alert_context,
    parse_o11y_alert_context,
    skip_reason,
)

logger = logging.getLogger(__name__)

INVESTIGATION_PROMPT = """An Observability alert was posted to Slack. Investigate it using Splunk
Observability MCP tools (o11y_*). Use the parsed identifiers below when querying alerts, metrics,
and traces. Summarize findings and recommended next steps.

Parsed from alert:
{parsed_context}

Full alert message:
{alert_text}
"""


def _should_process_alert(event: dict[str, Any], *, our_bot_user_id: str) -> bool:
    """Return True for top-level alert posts (including Splunk integration bot messages)."""
    return skip_reason(event, our_bot_user_id=our_bot_user_id) is None


def _build_investigation_prompt(alert_text: str) -> str:
    context = parse_o11y_alert_context(alert_text)
    return INVESTIGATION_PROMPT.format(
        parsed_context=format_o11y_alert_context(context),
        alert_text=alert_text.strip(),
    )


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

    @app.event("message")
    def handle_message(event: dict[str, Any], say: Any, client: WebClient) -> None:
        if event.get("channel") != channel_id:
            return
        reason = skip_reason(event, our_bot_user_id=our_bot_user_id)
        if reason:
            logger.info(
                "Skipped message ts=%s subtype=%s: %s",
                event.get("ts"),
                event.get("subtype"),
                reason,
            )
            return

        message_ts = event.get("ts")
        if not isinstance(message_ts, str):
            return
        if message_ts in processed:
            return
        processed.add(message_ts)

        text = extract_message_text(event)
        if not text.strip():
            return

        logger.info("Processing alert message ts=%s", message_ts)
        alert_context = parse_o11y_alert_context(text)
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
