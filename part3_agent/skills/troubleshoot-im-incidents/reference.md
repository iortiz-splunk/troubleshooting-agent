# Common infrastructure metrics (reference)

Supporting detail for **troubleshoot-im-incidents**. Use this list to **brainstorm adjacent signals** when an alert fires—not as a guarantee that every name exists in every org.

**Source of truth in your tenant:** call **`o11y_get_metric_names`** (O11y MCP) with filters derived from alert dimensions, or confirm names in **Metric Finder** / detector Program Editor. Collector and integration versions change metric MTEK names slightly (OpenTelemetry Kubernetes / host receivers, cloud exporter, legacy Smart Agent).

---

## How to use alongside an incident

| Step | Action |
|------|--------|
| 1 | Start from **`originatingMetric`** on the alert. |
| 2 | Add **same dimensions** as the alert (`k8s.pod.name`, `k8s.namespace.name`, `k8s.node.name`, `host.name`, `container.id`, etc.). |
| 3 | Pull **paired** metrics: e.g. CPU alert → memory + throttle + **network I/O** on the same entity to spot saturation, retries, or noisy neighbors. |
| 4 | For **network** symptoms or “slowness + IM” stories, chart **bytes/errors/drops** in/out and compare **node vs pod** scope. |

---

## Kubernetes / workload health (common)

| Metric (pattern) | Typical use |
|------------------|-------------|
| `k8s.container.restarts` | CrashLoop, instability, probe failures |
| `k8s.pod.ready` *(or equivalent readiness MTEK in tenant)* | Scheduling / readiness churn |
| Phase / status derived signals | Stuck Pending, Failed pods (names vary) |
| Object / API metrics (*if collected*) | Control plane or API stress |

---

## Container cgroup / resources (common)

| Metric (pattern) | Typical use |
|------------------|-------------|
| `container.cpu.utilization` | Per-container CPU vs limit |
| `container.memory.usage` | Working set / usage vs limit |
| CPU throttling / throttled seconds *(tenant-specific name)* | Limit too low vs real workload |
| `container.disk.io` *(or `container.blockio.*`)* | Disk-heavy workloads, ephemeral volume pressure |
| **`container.network.io`**, **`container.network.bytes`**, or **`network.*` scoped by container/pod dimensions** | **East-west traffic, egress bursts, correlation with latency** |

---

## Host / node (common)

| Metric (pattern) | Typical use |
|------------------|-------------|
| `system.cpu.utilization` | Node saturation, noisy neighbor context |
| `system.memory.utilization`, `system.memory.usage` | Memory pressure, OOM risk |
| `disk.summary.utilization` *(or `system.disk.*`)* | Disk full, inode issues |
| **`system.network.io`**, **`network.total.bytes`**, **`network.bytes`**, **`system.network.bytes`*** | **Node-level throughput; pair with errors/drops if exported** |
| **`system.network.errors`**, **`network.*errors*`**, **`system.network.dropped`** *(if present)* | **Packet drops, NIC/driver issues, congestion** |

\*Exact host network MTEKs differ by OS monitor (Linux host metrics vs cloud host metadata).

---

## Network-focused troubleshooting (keep in mind)

Symptoms that often warrant **network metrics** in the same time window:

- Elevated latency in APM while CPU/memory look “fine” on the service pod.
- Sporadic **timeouts**, **connection resets**, or **retry storms** (check bytes + errors + drops).
- **Cross-AZ/egress** cost or bandwidth limits (especially batch/worker pods).
- **Same node** hosting many chatty pods—correlate **`k8s.node.name`** with node **`system.network.*`** and per-container **`container.network.*`**.

If pod-level network series are missing, fall back to **node-level** network metrics and **K8s/CNI logs** (Splunk) for the incident window.

---

## Cloud / load balancer (when dimensions include `cloud.*`)

Patterns are highly provider-specific (e.g. AWS, GCP, Azure). Typical families:

- ALB/NLB / API gateway: request counts, latency, error rates, **processed bytes**.
- NAT / egress / VPN: bytes, drops, session limits.
- Use alert **`customProperties`** (`cloud.region`, `cloud.availability_zone`) with **`o11y_get_metric_names`** to list what exists.

---

## Frequently seen in sample IM alerts (this workspace)

From observed O11y alerts: `k8s.container.restarts`, `container.cpu.utilization`, `system.memory.usage`, `memory.utilization`. Treat these as **high-priority candidates** when matching detector types (restarts, CPU, memory) but still **verify in tenant**.
