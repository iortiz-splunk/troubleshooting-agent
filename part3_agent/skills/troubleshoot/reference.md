# Alert product categorization reference

Supporting detail for the **troubleshoot** skill (step 2 — categorize). For **when to run troubleshoot** (triggers, IDs, URLs), see [SKILL.md](SKILL.md) “When to apply”.

Patterns below are derived from Splunk Observability Cloud alerts and standard O11y product signals. Use them to classify an alert as **APM**, **IM**, **Synthetics**, or **RUM** before **troubleshoot-apm-incidents**, **troubleshoot-im-incidents**, **troubleshoot-synthetics-incidents**, or **troubleshoot-rum-incidents** as appropriate.

---

## Field sources

For each alert (from **o11y_search_alerts_or_incidents** or incident UI):

- **originatingMetric** — Metric that triggered the detector (e.g. `k8s.container.restarts`, `request.count`).
- **customProperties** — Dimensions and tags on the alert (e.g. `k8s.pod.name`, `sf_service`, `host.name`).
- **detector** / **detectLabel** — Detector display name and label (e.g. "Pod CrashLoop ImagePullBackOff", "Service latency high").

---

## IM (Infrastructure Monitoring)

| Signal | Pattern |
|--------|--------|
| **originatingMetric** | `k8s.*` (e.g. `k8s.container.restarts`), `system.*` (e.g. `system.memory.usage`), `container.*` (e.g. `container.cpu.utilization`), `memory.utilization`, host/cpu/memory/disk/network metrics |
| **customProperties** | Any of: `k8s.cluster.name`, `k8s.namespace.name`, `k8s.pod.name`, `k8s.container.name`, `k8s.deployment.name`, `k8s.node.name`, `host.name`, `host.id`, `container.id`, `cloud.provider`, `cloud.region` |
| **detector / detectLabel** | Pod, container, node, host, CPU, memory, disk, cluster, CrashLoop, ImagePullBackOff, GMSA, namespace, CSI, connectivity, restarts |

**Observed in sample:** 100/100 alerts were IM (metrics: `k8s.container.restarts`, `container.cpu.utilization`, `system.memory.usage`, `memory.utilization`; detectors: Pod Restart High, GMSA Spec Mismatch, Pod CrashLoop ImagePullBackOff, POD Error Logs Namespace Events, Pod/Container High CPU Usage, CSI Driver Pod Connectivity, Memory).

---

## APM (Application Performance Monitoring)

| Signal | Pattern |
|--------|--------|
| **originatingMetric** | Request/latency/error metrics (e.g. `request.count`, `request.latency`, error rate), throughput, or APM-built-in metric names |
| **customProperties** | `sf_service` (service name), or service-related dimensions; may include `sf_environment`; often accompanied by infra dimensions (host, k8s) for correlation |
| **detector / detectLabel** | Service name, latency, errors, throughput, request rate, dependency, health |

---

## RUM (Real User Monitoring)

| Signal | Pattern |
|--------|--------|
| **originatingMetric** | RUM metrics (e.g. page load, session, error counts); often prefixed or scoped to RUM |
| **customProperties** | RUM app name, page, session, browser, or other RUM-specific dimensions |
| **detector / detectLabel** | RUM, page load, session, front-end, browser, app name |

---

## Synthetics

| Signal | Pattern |
|--------|--------|
| **originatingMetric** | Synthetic/availability metrics (e.g. check success/failure, journey result) |
| **customProperties** | Check name, journey name, location, or other synthetic dimensions |
| **detector / detectLabel** | Synthetic, check, journey, availability, uptime |

---

## Decision order

1. Check **originatingMetric** for product-specific prefixes or names (k8s/system/container → IM; request/latency/error with service context → APM; rum/synthetic → RUM/Synthetics).
2. Check **customProperties** for `sf_service` (APM), `k8s.*`/`host.*`/`container.*` (IM), or RUM/Synthetics dimensions.
3. Use **detector** / **detectLabel** when metric and properties are ambiguous (e.g. "Pod High CPU" → IM; "Service latency critical" → APM).
