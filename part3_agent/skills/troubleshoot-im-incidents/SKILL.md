---
name: troubleshoot-im-incidents
description: Guides troubleshooting of Infrastructure alerts or incidents in Splunk Observability Cloud using the O11y MCP server. Use when the user asks to troubleshoot, investigate, or find the root cause of an Infrastructure incident or alert.
---

# Troubleshoot Infrastructure alerts or incidents

Use **Splunk Observability MCP** (`o11y_*` tools) and **Splunk Enterprise MCP** where needed: correlate **infrastructure metrics** (hosts, Kubernetes, containers, cloud) with **demand from applications** (APM dependencies, trace volume) and **logs** around the incident time.

## When to use

- User asks to **troubleshoot**, **investigate**, or find the **root cause** of an infrastructure-related incident or alert.
- Alert signals include metrics such as `k8s.*`, `system.*`, `container.*`, or dimensions like `host.name`, `k8s.pod.name`, `k8s.namespace.name`.
- The user suspects **capacity**, **noisy neighbors**, **rollouts**, or **downstream slowness** driving IM symptoms (CPU, memory, restarts, disk, network saturation).

## Investigation framing (IM)

Work in layers; state which layer Evidence supports.

| Layer | Question | Typical signals |
|-------|----------|-----------------|
| **Symptom** | What metric fired, on which entity? | `originatingMetric`, `detectLabel`, `customProperties` |
| **Scope** | One pod vs many? One node vs cluster? | Group by `k8s.node.name`, `k8s.workload.name`, AZ |
| **Capacity / limits** | Throttled, OOM, disk pressure, cgroup limits? | Limits in K8s events/logs; `container.*`, node allocatable |
| **Change / churn** | Deploy, HPA, CronJob, node issue? | Restarts, new `k8s.pod.uid`, job schedule, correlated IM alerts |
| **Demand / dependencies** | Did callers or backends change behavior? | APM deps, trace rate/latency shifts, outbound errors (see below) |

Do not stop at “high CPU on pod X” without asking whether **work increased** (demand), **efficiency dropped** (code/config), or **limits tightened**—dependency and traffic analysis supports the demand side.

## Dependency and demand-side checks (required when plausible)

After scoped metrics, **explicitly consider** whether a **dependency or caller change** could explain the symptom (more work, retries, backlog).

1. **Map infra entity → APM context (when possible)**  
   - From alert dimensions: `k8s.namespace.name`, `k8s.workload.name`, `k8s.deployment.name`, `k8s.container.name`, `k8s.cluster.name`.  
   - **Environment:** `o11y_get_apm_environments` (e.g. cluster or org naming like `ai-pod` may map to `sf_environment`; confirm in UI).  
   - **Service:** `o11y_get_apm_services` for that environment—try exact `sf_service` names if known; if the firing workload is *not* an APM service (many CronJobs, agents, loadgens), note that **APM dependency graphs do not attach to the pod** unless it emits traces or matches a service name.

2. **Dependencies**  
   - For each traced service tied to the same namespace/product area: `o11y_get_apm_service_dependencies` with **`service_name`** + **`environment_name`**.  
   - **Dependency *changes*:** compare **at least two windows**—for example the **incident window** vs **prior baseline** (same length, earlier week or day). Note shifts in **outbound** callee request volume, **P90/P99 latency**, and **errorCount** on edges (Milvus, DB, internal APIs, LLM services, etc.). A backend slowing down can increase **client-side** CPU (retries, parsing, concurrency) even when the IM alert only names the pod.  
   - If the incident window returns **empty** dependencies but a longer window does not, call out **sparse tracing** in that slice; do not conclude “no dependencies”—use SignalFlow, logs, or traces as fallback.

3. **When there is no APM service for the firing pod**  
   - Correlate **caller** services (e.g. `rag-server`) **request rate / latency** via APM or **o11y_execute_signalflow_program** on relevant RED-ish or custom metrics for the same timestamp range.  
   - Check **Splunk** for the CronJob/Deployment definition (what binary/API it hits) and pod logs in the incident window.

4. **Document**  
   In the report: whether dependency analysis **was applicable**, **what was compared** (windows), and **whether deps implicated or ruled out** demand-side RCA.

## Recommended workflow

- **o11y_search_alerts_or_incidents** or **get-alerts-or-incidents** to load the alert payload (`originatingMetric`, `customProperties`, `incidentId`, `detectorId`, `link`).
- **o11y_get_metric_names** / **o11y_execute_signalflow_program** (or **o11y_generate_signalflow_program** **then** execute after validation) for the firing metric and key dimensions from the alert; add **adjacent** signals on the same entity (e.g. CPU + throttling + memory + **network I/O or errors** on the same `k8s.pod.name` / `k8s.node.name`). For a quick menu of commonly monitored IM metrics—including **network**—see [reference.md](reference.md); **confirm names in your org** with `o11y_get_metric_names`.
- **Dependency / demand** — follow [Dependency and demand-side checks](#dependency-and-demand-side-checks-required-when-plausible).
- **search-logs** (required): **`splunk_run_query`** for host/pod/container logs in the incident window; include K8s events if indexed. See **search-logs** skill for SPL patterns.
- Narrow time range and add dimensions (cluster, namespace, workload, node) as scope tightens.

## Final step

Format the outcome with the **troubleshoot-report** skill: alert context, identifiers, timestamps, links (detector/incident, dashboards if returned), concise RCA (**including dependency/demand findings or explicit N/A**), and next steps.
