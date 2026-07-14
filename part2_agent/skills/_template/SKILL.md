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
1. First MCP tool — params to set (service_name, environment_name, time_range)
2. Second MCP tool — what evidence it provides

## Interpretation
- Bullet on how to read the metrics
- Bullet on what changed vs baseline

## Do not
- Guardrails the agent should follow (e.g. never search without service_name)
