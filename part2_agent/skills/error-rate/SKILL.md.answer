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

## Tool sequence (required — complete both steps)

1. **o11y_search_alerts_or_incidents** (optional context)
   - `params.service_name` — exact APM service
   - `params.environments` — list, e.g. `["sre-agent-workshop"]`
   - `params.time_range` — `{"start": "-1h", "stop": "now"}`
   - **Do not** set `params.severity` unless the user explicitly asked for a severity filter.
   - If you must filter severity, use a **list**: `["critical"]` — never a bare string.
   - Capture `eventId` when alerts exist; if `alerts` is empty, **continue to step 2**.

2. **o11y_get_apm_service_errors_and_requests** (required — always run)
   - `params.service_name`, `params.environment_name`, `params.time_range`
   - Run this even when step 1 returned no alerts — CLI investigations often have no active detector.
   - Do **not** write your final investigation-report until this tool returns.

## Interpretation
- Compare error count vs request volume
- Note if errors spike with traffic or independently
- Elevated errors with stable request volume suggests a fault in the service, not load

## Workshop gap (Part 2)
- Does not map downstream dependencies — see Part 3 service-dependencies skill
- Splunk log search (`splunk_run_query`, index `k8s-apps`) is required in Part 3 — optional stretch here

## Do not
- Stop after empty alert search — always run step 2 metrics
- Conclude root cause without metric evidence from tools
- Add params.severity unless the user explicitly requested it (use a list if needed)
- Ask the user "would you like metrics?" — call step 2 yourself
