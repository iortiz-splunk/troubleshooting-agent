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
User or alert mentions high latency, duration, or p99 on an APM service.

## Tool sequence (required — complete both steps)

1. **o11y_search_alerts_or_incidents** (optional context)
   - `params.service_name` — exact APM service
   - `params.environments` — list, e.g. `["sre-agent-workshop"]`
   - `params.time_range` — `{"start": "-1h", "stop": "now"}`
   - **Do not** set `params.severity` unless the user explicitly asked for a severity filter.
   - If you must filter severity, use a **list**: `["critical"]` — never a bare string.
   - Capture `eventId` when alerts exist; if `alerts` is empty, **continue to step 2**.

2. **o11y_get_apm_service_latency** (required — always run)
   - `params.service_name`, `params.environment_name`, `params.time_range`
   - Run this even when step 1 returned no alerts — CLI investigations often have no active detector.
   - Do **not** write your final investigation-report until this tool returns.

## Interpretation
- p50 vs p99 widening suggests tail latency vs uniform slowdown
- Compare to baseline window if alert includes threshold
- No active alert + elevated p99 in metrics still counts as a latency finding

## Workshop gap (Part 2)
- Does not include exemplar trace pull — add o11y_get_apm_exemplar_traces in Part 3

## Do not
- Stop after alert search — empty `alerts` is not a conclusion
- Search without service_name
- Add severity filter by default (narrows results and often returns empty)
- Ask the user "would you like metrics?" — call step 2 yourself
