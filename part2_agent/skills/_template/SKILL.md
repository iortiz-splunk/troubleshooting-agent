---
name: your-skill-name
description: One line — when the agent should use this playbook
alert_signals:
  - keyword1
  - keyword2
mcp_tools:
  - o11y_search_alerts_or_incidents
  - o11y_tool_name_here
---

# Your skill title

## When to use
Describe the alert types or symptoms that match this playbook.

## Tool sequence
1. First MCP tool (often alert search) — params: service_name, environments (list), time_range. Empty alerts is OK — **continue**.
2. Second MCP tool (metrics) — **required before final report**; do not ask the user for permission to run it.

## Interpretation
- Bullet on how to read the metrics
- Bullet on what changed vs baseline

## Do not
- Stop after empty alert search — always run the metrics step in this playbook
- Add params.severity unless the user explicitly requested it (must be a list if used)
- Guardrails the agent should follow (e.g. never search without service_name)
