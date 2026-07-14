---
name: latency-spike
description: Investigate APM latency alerts using o11y_get_apm_service_latency.
alert_signals:
  - latency
  - duration
  - p99
  - slow
rule_patterns:
  - "*latency*"
  - "*duration*"
mcp_tools:
  - o11y_search_alerts_or_incidents
  - o11y_get_apm_service_latency
---

# Latency spike investigation

## When to use
Alert mentions high latency, duration, or p99 on an APM service.

## Tool sequence
1. o11y_search_alerts_or_incidents — confirm active alert, capture eventId
2. o11y_get_apm_service_latency — service_name + environment_name + time_range

## Interpretation
- p50 vs p99 widening suggests tail latency vs uniform slowdown
- Compare to baseline window if alert includes threshold

## Workshop gap (Part 2)
- Does not include exemplar trace pull — add o11y_get_apm_exemplar_traces in Part 3

## Do not
- Search without service_name
