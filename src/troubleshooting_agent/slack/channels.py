"""Resolve Slack channel names to IDs."""

from __future__ import annotations

from typing import Any, cast

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from troubleshooting_agent.config import Settings


def resolve_alerts_channel_id(settings: Settings, client: WebClient) -> str:
    """Return the configured alerts channel ID."""
    if settings.slack_alerts_channel_id:
        return settings.slack_alerts_channel_id

    channel_name = settings.slack_alerts_channel_name.lstrip("#")
    cursor: str | None = None
    try:
        while True:
            response = client.conversations_list(
                types="public_channel",
                limit=200,
                cursor=cursor,
            )
            response_dict = cast(dict[str, Any], response)
            channels = cast(list[dict[str, Any]], response_dict.get("channels", []))
            for channel in channels:
                if channel.get("name") == channel_name:
                    channel_id = channel.get("id")
                    if isinstance(channel_id, str):
                        return channel_id
            metadata = cast(dict[str, Any], response_dict.get("response_metadata") or {})
            next_cursor = metadata.get("next_cursor")
            cursor = next_cursor if isinstance(next_cursor, str) and next_cursor else None
            if not cursor:
                break
    except SlackApiError as exc:
        msg = f"Failed to list channels: {exc.response['error']}"
        raise RuntimeError(msg) from exc

    msg = (
        f"Channel #{channel_name} not found. Create it, invite the bot, "
        "or set SLACK_ALERTS_CHANNEL_ID."
    )
    raise RuntimeError(msg)
