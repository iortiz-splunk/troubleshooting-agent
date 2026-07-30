---  
name: troubleshoot-apm-incidents  
description: Guides troubleshooting of APM alerts or incidents in Splunk Observability Cloud using the O11y MCP server. Use when the user asks to troubleshoot, investigate, or find the root cause of an APM incident or alert.  
---  

# Troubleshoot APM Alerts or Incidents  
Use **Splunk Observability MCP** (`o11y_*` tools) and **Splunk Enterprise MCP** where needed to gather data that helps find root cause: **APM data** (service health, request mix, latency, dependencies, traces), **infrastructure data** (CPU, memory, disk, network) for the same workload, and logs associated with the service around the time of the error. Correlating APM, Infrastructure, and logs data to determine the most likely cause of the errors  

## When to use  
- User asks to **troubleshoot**, **investigate**, or find the **root cause** of an APM incident, alert or service.  
- User refers to a detector, service, or incident by name.  

Identify **service name** and **environment** from the incident (e.g. alert `sf_service`, `sf_environment`) or via **o11y_search_alerts_or_incidents** if needed.  

## MCP parameter requirements (APM)  
All APM tools take a nested ``params`` object. Always include:  
- **params.service_name** — exact APM service name (e.g. from `sf_service`)  
- **params.environment_name** — exact environment (e.g. from `sf_environment`)  
- **params.time_range** — object like `{"start": "-1h", "stop": "now"}`  

**o11y_get_apm_exemplar_traces** also requires **params.exemplar_type** — use exactly one of:  
- `req` — request exemplars  
- `err` — error exemplars  
- `rc_err` — root-cause error exemplars  
- `lat_buck_` — latency-bucket exemplars (for latency alerts; note trailing underscore)  

Do **not** use `latency`, `lat_buck`, `lat_buck_99`, or other invented values. If exemplar traces fail after one retry with the correct literal, continue with latency/error breakdown tools and summarize without exemplars.  

## Recommended Workflow (call each tool at most once)

Use one shared **params.time_range** (e.g. `{"start": "-1h", "stop": "now"}`) for all steps below. **Do not** re-call the same tool with a narrower window unless the first call failed validation.

1. **o11y_get_apm_service_errors_and_requests** — error/request breakdown (primary for error-rate alerts).
2. **o11y_get_apm_service_latency** — only if latency context is needed (latency alerts or high P99 in step 1).
3. **o11y_get_apm_exemplar_traces** — `exemplar_type`: `err` or `rc_err` for error alerts; `lat_buck_` for latency alerts.
4. **o11y_get_apm_trace_tool** — optional, only if you have a trace_id from step 3 worth inspecting.
5. Skip **o11y_get_apm_services** unless steps 1–3 lack service health summary.

Do **not** call **o11y_get_apm_service_errors_and_requests** again with `-30m` after already fetching `-1h` unless the first call errored.

## Log search (required before concluding)

After APM metrics/traces, apply **search-logs** using **Splunk platform MCP** (`splunk_*` tools — not `o11y_*`):

1. Read the **log index catalog** in your prompt (`indexes.md`) for `default_index`, `service_aliases`, and example SPL.
2. Build SPL from **`sf_service`** (mapped to container sourcetype), alert time, and **trace_id** / K8s tags from APM tools.
3. Run **`splunk_run_query`** once with narrow SPL; widen once if `total_rows` is 0 (try `httpevent`).
4. Only if catalog queries return zero rows: **`splunk_get_metadata`** (`type=sourcetypes`) — avoid **`splunk_get_indexes`** unless index is unknown.

**Do not** finish the investigation without this step when Splunk MCP tools are available.

## Root cause analysis  
Use the gathered data to form a view of root cause and recommendations (traffic mix, dependencies, tail latency, resource pressure, etc.).  

**Final step:** Present results using the **troubleshoot-report** skill (standard sections: alert/incident, identifiers, timestamps, links, summary, concise RCA, next steps). Pull links from MCP responses (service pages, trace analyzer, trace IDs).  