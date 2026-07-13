"""Slack connectivity checks."""

from __future__ import annotations

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from troubleshooting_agent.config import Settings
from troubleshooting_agent.slack.channels import resolve_alerts_channel_id


def check_slack_health(settings: Settings) -> tuple[bool, str | None]:
    """
    Verify Slack bot token and alerts channel access.

    Returns:
        (ok, error_message)
    """
    if not settings.slack_bot_token:
        return False, "SLACK_BOT_TOKEN is not set"

    client = WebClient(token=settings.slack_bot_token)
    try:
        auth = client.auth_test()
        team = auth.get("team")
        bot = auth.get("user")
    except SlackApiError as exc:
        return False, f"auth.test failed: {exc.response['error']}"

    try:
        channel_id = resolve_alerts_channel_id(settings, client)
        history = client.conversations_history(channel=channel_id, limit=1)
        _ = history
    except SlackApiError as exc:
        if exc.response.get("error") != "not_in_channel":
            return False, str(exc)
        try:
            client.conversations_join(channel=channel_id)
        except SlackApiError as join_exc:
            join_err = join_exc.response.get("error", "unknown")
            return False, (
                f"Bot is not in the alerts channel (not_in_channel). "
                f"Auto-join failed ({join_err}). "
                f"In #{settings.slack_alerts_channel_name}, run: /invite @your-bot-name"
            )
        try:
            client.conversations_history(channel=channel_id, limit=1)
        except SlackApiError as exc:
            return False, str(exc)
    except RuntimeError as exc:
        return False, str(exc)

    team_name = team if isinstance(team, str) else "unknown"
    bot_name = bot if isinstance(bot, str) else "bot"
    channel_label = settings.slack_alerts_channel_id or f"#{settings.slack_alerts_channel_name}"
    return True, f"workspace={team_name} bot={bot_name} channel={channel_label} id={channel_id}"
