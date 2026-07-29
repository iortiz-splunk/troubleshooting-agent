"""MCP server selection for load tests (independent of .env enable flags)."""

from __future__ import annotations

from dataclasses import dataclass

from workshop_shared.config import Settings


@dataclass(frozen=True)
class McpServerSelection:
    """Which Splunk MCP integrations to exercise in a load test."""

    use_o11y: bool = True
    use_cloud: bool = False

    def __post_init__(self) -> None:
        if not self.use_o11y and not self.use_cloud:
            msg = "At least one MCP server must be selected (O11y and/or Splunk Cloud)"
            raise ValueError(msg)

    @property
    def label(self) -> str:
        parts: list[str] = []
        if self.use_o11y:
            parts.append("Splunk O11y Cloud")
        if self.use_cloud:
            parts.append("Splunk Cloud (logs)")
        return " + ".join(parts)

    @classmethod
    def from_server_names(cls, names: str) -> McpServerSelection:
        """Parse comma-separated names: o11y, cloud (case-insensitive)."""
        tokens = {part.strip().lower() for part in names.split(",") if part.strip()}
        if not tokens:
            msg = "At least one server name required: o11y, cloud"
            raise ValueError(msg)
        unknown = tokens - {"o11y", "cloud"}
        if unknown:
            msg = f"Unknown server name(s): {', '.join(sorted(unknown))}. Use: o11y, cloud"
            raise ValueError(msg)
        return cls(use_o11y="o11y" in tokens, use_cloud="cloud" in tokens)


def apply_server_selection(settings: Settings, selection: McpServerSelection) -> Settings:
    """Override MCP enable flags for this load test run only."""
    return settings.model_copy(
        update={
            "enable_splunk_o11y": selection.use_o11y,
            "enable_splunk_cloud_mcp": selection.use_cloud,
            "enable_splunk_mcp": False,
        }
    )
