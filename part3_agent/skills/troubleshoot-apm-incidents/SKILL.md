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

## Recommended Workflow  
- **o11y_get_apm_services**: Aggregate request count, error count, latency (e.g. P50/P90/P99), health for the service and environment.  
- **o11y_get_apm_service_latency**: Latency by endpoint, workflow, or other dimensions to spot slow operations or tail latency.  
- **o11y_get_apm_service_errors_and_requests**: Breakdown by tag (endpoint, http status, workflow, etc.) to see what changed or dominates (e.g. 200 vs 4xx, by operation). Also check for **infrastructure-related tags** (host.name, k8s.pod.name, k8s.namespace.name, etc.)—if non-null, they support correlation; if all null, infrastructure identity may be available only from full trace process tags.  
- **o11y_get_apm_exemplar_traces**: Sample traces (e.g. by exemplar type: req, err, rc_err, or latency bucket) to see span composition, slow or failing operations, and to obtain **trace IDs** for full trace detail.  
- **o11y_get_apm_trace_tool**: Full trace by trace_id. Use to inspect a specific request and to read **process** (resource) tags for the incident service—host, K8s (pod, node, namespace, deployment), container, deployment.environment—for infrastructure correlation and for filtering infrastructure metrics in SignalFlow when service/environment filters return no data.  
- get logs: Utilize the Splunk MCP server to find looks related to the service around the time errors were happening.  
- get infrastructure metrics: **o11y_get_metric_names** to discover metric names (e.g. by service name, “request”, “redis”, "CPU Utilization') to identify relevant metrics for troubleshooting.  
- **o11y_execute_signalflow_program**: Run SignalFlow to get the metrics identified in the previous step, or any metric time series. Prefer **o11y_generate_signalflow_program** when the agent needs a program that filters by service/environment or by infra dimensions from a trace.  

## Root cause analysis  
Use the gathered data to form a view of root cause and recommendations (traffic mix, dependencies, tail latency, resource pressure, etc.).  

**Final step:** Present results using the **troubleshoot-report** skill (standard sections: alert/incident, identifiers, timestamps, links, summary, concise RCA, next steps). Pull links from MCP responses (service pages, trace analyzer, trace IDs).  