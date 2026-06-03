"""
Slack integration stub (Phase 3).

Planned flow: receive error/failure notifications, normalize to incident context,
invoke the agent, reply in thread.

Required env: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET
Enable with: ENABLE_SLACK=true
"""

from langchain_core.tools import BaseTool

from troubleshooting_agent.config import Settings


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Return Slack-related tools when implemented."""
    return []
