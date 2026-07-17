---
tenant: o11y-workshop-amer
gateway_region: region-pdx10
discovered_at: "2026-07-17"
default_index: splunk4rookies-workshop
do_not_use:
  - index: _internal
    reason: Splunk platform logs (splunkd, mongod, mcp_server) — not application data
  - index: _introspection
    reason: Splunk introspection metrics — not application data
  - index: main
    reason: Disabled in tenant listing; application logs are in splunk4rookies-workshop
products:
  apm:
    primary_index: splunk4rookies-workshop
    secondary_indexes:
      - splunk-arcade
    sourcetypes:
      - httpevent
      - "kube:container:*"
      - json
    notes:
      - "Map sf_service to sourcetype kube:container:<lowercase-hyphenated> when it exists (e.g. paymentservice, checkoutservice, frontend)."
      - "Many APM service names (e.g. Verification) do not have a matching kube:container sourcetype — search httpevent _raw and json message/trace_id instead."
      - "sf_environment (e.g. Brian-E-AD-Capital) may not appear in log fields; prefer pod/namespace/workload tags from APM traces."
      - "Structured kube logs use JSON in _raw: http.resp.status, http.resp.took_ms, severity, message, trace_id."
    common_kube_containers:
      - frontend
      - paymentservice
      - payment
      - checkoutservice
      - cartservice
      - shippingservice
      - recommendationservice
      - adservice
      - emailservice
      - travel-planner-langchain
      - fraud-detection
      - product-reviews
    example_spl: |
      index=splunk4rookies-workshop earliest=-1h latest=now
      (sourcetype="kube:container:paymentservice" OR sourcetype=httpevent)
      (severity=error OR http.resp.status>=400 OR _raw="*error*")
      | head 50
  im:
    primary_index: splunk4rookies-workshop
    sourcetypes:
      - kube:events
      - "kube:container:*"
      - auth_log
      - syslog
    notes:
      - "kube:events has pod restart/back-off messages (search _raw for pod name from alert)."
      - "Container logs use source paths like /var/log/pods/<namespace>_<pod>_<uid>/<container>/0.log."
    example_spl: |
      index=splunk4rookies-workshop earliest=-1h latest=now
      (sourcetype=kube:events OR sourcetype="kube:container:*")
      _raw="*Back-off*" OR _raw="*Failed*"
      | head 50
  rum:
    primary_index: splunk4rookies-workshop
    secondary_indexes:
      - splunk-arcade
    sourcetypes:
      - httpevent
      - "kube:container:frontend"
      - "kube:container:rum-loadgen"
      - json
    notes:
      - "Backend API logs for RUM sessions often appear in httpevent or kube:container:frontend."
      - "Arcade demo uses index splunk-arcade with deployment.environment (e.g. gameify) in json logs."
    example_spl: |
      index=splunk4rookies-workshop earliest=-1h latest=now
      (sourcetype=httpevent OR sourcetype="kube:container:frontend")
      (http.resp.status>=400 OR _raw="*error*")
      | head 50
  synthetics:
    primary_index: splunk4rookies-workshop
    secondary_indexes:
      - splunk-arcade
    sourcetypes:
      - httpevent
      - "kube:container:*"
      - json
    notes:
      - "Search target path/host and 5xx during the check failure window."
      - "httpevent _raw includes Envoy-style access lines with status codes."
    example_spl: |
      index=splunk4rookies-workshop earliest=-1h latest=now
      sourcetype=httpevent (status>=500 OR _raw="* 5*")
      | head 50
---

# Log index catalog — o11y-workshop-amer

Facilitator-maintained reference from Splunk Cloud MCP discovery (`splunk_get_indexes`, `splunk_run_query`). The investigate agent reads this **before** probing the cluster.

## Default

| Setting | Value |
|---------|-------|
| **Default index** | `splunk4rookies-workshop` |
| **Tenant** | `o11y-workshop-amer` |
| **Last verified** | 2026-07-17 |

## Do not use for app troubleshooting

| Index | Why |
|-------|-----|
| `_internal` | Splunk platform (`splunkd`, `mongod`, `mcp_server`) |
| `_introspection` | Splunk introspection only |
| `main` | Disabled; no application events in last 7d |

## Index summary (24h event volume)

| Index | Role | Top sourcetypes |
|-------|------|-----------------|
| `splunk4rookies-workshop` | **Primary** — Hipster Shop / workshop K8s + HTTP | `kube:container:*`, `httpevent`, `kube:events` |
| `splunk-arcade` | Arcade demo app | `json`, `arcade:app:logs`, `otel` |

## Product → index / sourcetype

### APM

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `httpevent`, `kube:container:*`, `json` | Start here for latency/error alerts |
| `splunk-arcade` | `json`, `otel` | Only when alert service matches arcade apps |

**Service mapping:** try `sourcetype="kube:container:<lowercase(sf_service)>"` first. If zero rows, search `httpevent` / `json` with `_raw="*<service>*"` or `trace_id` from APM exemplar traces.

**Common `kube:container:` sourcetypes (7d):** `frontend`, `currencyservice`, `paymentservice`, `cartservice`, `checkoutservice`, `shippingservice`, `payment`, `adservice`, `recommendationservice`, `travel-planner-langchain`, `fraud-detection`, `product-reviews`, `accounting`, `emailservice`, `kafka`, `redis`.

### IM (Infrastructure Monitoring)

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `kube:events`, `kube:container:*`, `auth_log`, `syslog` | Pod restarts, back-off, node/auth issues |

### RUM

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `httpevent`, `kube:container:frontend`, `kube:container:rum-loadgen` | Backend correlated with RUM sessions |
| `splunk-arcade` | `json` | `deployment.environment`, `service.name`, `trace_id` in JSON |

### Synthetics

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `httpevent`, `kube:container:*` | Target URL path + HTTP status during failure window |

## Field hints (from sample events)

| Sourcetype | Useful fields |
|------------|---------------|
| `kube:container:*` | JSON in `_raw`: `message`, `severity`, `http.resp.status`, `http.resp.took_ms`, `http.req.path`, `trace_id`, `timestamp` |
| `httpevent` | Envoy access lines in `_raw`; app text messages (`User accessing index page`, checkout messages) |
| `json` (arcade) | `service.name`, `deployment.environment`, `level`, `message`, `trace_id`, `event` |
| `kube:events` | `_raw` pod/event text (`Back-off restarting failed container ...`) |

## Refreshing this catalog

From a facilitator machine with AMER Splunk MCP connected:

1. `splunk_get_indexes` — confirm enabled indexes and defaults.
2. `index=<name> earliest=-24h | stats count by sourcetype | sort - count` — volume by sourcetype.
3. Sample events: `| head 3` per sourcetype to capture field names.
4. Update YAML frontmatter and tables; run `pytest tests/part3/test_skill_tools.py`.

See [indexes.example.md](indexes.example.md) for a tenant-agnostic template.
