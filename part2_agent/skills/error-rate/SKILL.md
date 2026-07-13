---
name: error-rate
description: Investigate error-rate alerts using o11y_get_apm_service_errors_and_requests.
alert_signals:
  - error
  - errors
  - 5xx
rule_patterns:
  - "*error*"
  - "*5xx*"
mcp_tools:
  - o11y_search_alerts_or_incidents
  - o11y_get_apm_service_errors_and_requests
---

# Error rate investigation

## When to use
Detector or Slack text mentions elevated errors or error rate.

## Tool sequence
1. o11y_search_alerts_or_incidents — confirm alert, capture eventId
2. o11y_get_apm_service_errors_and_requests — service_name, environment_name, time_range

## Interpretation
- Compare error count vs request volume
- Note if errors spike with traffic or independently

## Workshop gap (Part 2)
- Does not map downstream dependencies — see Part 3 service-dependencies skill

## Do not
- Conclude root cause without metric evidence
