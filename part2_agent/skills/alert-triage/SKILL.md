---
name: alert-triage
description: Parse Slack O11y alerts and confirm active incidents via o11y_search_alerts_or_incidents.
alert_signals:
  - alert
  - incident
  - triggered
rule_patterns:
  - "*"
mcp_tools:
  - o11y_search_alerts_or_incidents
---

# Alert triage

## When to use
Any Splunk Observability alert from Slack before deeper investigation.

## Required context
- sf_service, sf_environment (exact APM names)
- time_range: {"start": "-1h", "stop": "now"}

## Tool sequence
1. o11y_search_alerts_or_incidents — params.service_name, params.environment_name, params.time_range
2. Capture eventId from results for cross-referencing in Observability Cloud

## Response template
- Alert status (active / cleared)
- Service and environment
- Recommended next playbook (latency vs errors)

## Do not
- Search without service_name
- Use time_range as a bare string
