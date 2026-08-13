---
tenant: o11y-workshop-amer
gateway_region: region-pdx10
discovered_at: "2026-07-29"
default_index: splunk4rookies-workshop
service_aliases:
  payment: payment
  paymentservice: payment
  cart: cart
  cartservice: cart
  ad: ad
  adservice: ad
  email: email
  emailservice: email
  currency: currency
  currencyservice: currency
  recommendation: recommendation
  recommendationservice: recommendation
  productcatalogservice: product-catalog
  product-catalog: product-catalog
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
    notes:
      - "Container sourcetypes use short K8s container names (payment, cart, ad) — NOT *service suffix (paymentservice returns zero rows)."
      - "Map sf_service via service_aliases in this catalog, or strip trailing 'service' (paymentservice → payment)."
      - "Many APM service names (e.g. Verification) have no kube:container match — search httpevent _raw or trace_id from exemplars."
      - "splunk_run_query returns JSON {results, total_rows}; zero rows is ~47 bytes, not an error."
    common_kube_containers:
      - frontend
      - payment
      - cart
      - ad
      - email
      - currency
      - recommendation
      - fraud-detection
      - product-catalog
      - product-reviews
      - accounting
      - kafka
      - llm
      - quote
      - traefik
    example_spl: |
      index=splunk4rookies-workshop earliest=-1h latest=now
      (sourcetype="kube:container:payment" OR sourcetype=httpevent)
      (severity=error OR http.resp.status>=400 OR _raw="*error*" OR _raw="*Invalid token*")
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
    notes:
      - "Search target path/host and 5xx during the check failure window."
      - "httpevent _raw includes Envoy-style access lines with status codes."
    example_spl: |
      index=splunk4rookies-workshop earliest=-1h latest=now
      sourcetype=httpevent (status>=500 OR _raw="* 5*")
      | head 50
---

# Log index catalog — o11y-workshop-amer

Facilitator-maintained reference from Splunk Cloud MCP discovery (`splunk_get_indexes`, `splunk_get_metadata`, `splunk_run_query`). The investigate agent reads this **before** probing the cluster.

## Default

| Setting | Value |
|---------|-------|
| **Default index** | `splunk4rookies-workshop` |
| **Tenant** | `o11y-workshop-amer` |
| **Last verified** | 2026-07-29 (Splunk Cloud MCP live probe) |

## Do not use for app troubleshooting

| Index | Why |
|-------|-----|
| `_internal` | Splunk platform (`splunkd`, `mongod`, `mcp_server`) |
| `_introspection` | Splunk introspection only |
| `main` | Disabled; no application events |

## Index summary (24h event volume)

| Index | Role | Top sourcetypes |
|-------|------|-----------------|
| `splunk4rookies-workshop` | **Primary** — Hipster Shop / workshop K8s + HTTP | `httpevent` (~612k), `kube:container:*` |
| `splunk-arcade` | Arcade demo app | `json`, `arcade:app:logs`, `otel` |

## MCP tool shapes (Splunk Cloud)

**`splunk_run_query`** — flat args (not `params`):

```json
{
  "query": "index=splunk4rookies-workshop sourcetype=\"kube:container:payment\" _raw=\"*error*\" | head 20",
  "earliest_time": "-1h",
  "latest_time": "now",
  "row_limit": 50
}
```

**Time:** use relative `earliest_time`/`latest_time` on the tool call (`-1h`, `-40m`, `now`). **Never** put O11y ISO timestamps (`2026-07-30T14:17:20.000Z`) in SPL `earliest=`/`latest=` — Splunk rejects them.

**Response:** `{"results": [{ "_raw", "_time", "sourcetype", "source", "host", "index", ... }], "total_rows": N, "truncated": false}`. Zero hits: `{"results":[],"total_rows":0}` (~47 bytes) — widen sourcetype or search `httpevent`, do not retry the same SPL.

**`splunk_get_metadata`** — list sourcetypes when catalog is stale:

```json
{"type": "sourcetypes", "index": "splunk4rookies-workshop", "earliest_time": "-24h", "latest_time": "now", "row_limit": 100}
```

## Product → index / sourcetype

### APM

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `httpevent`, `kube:container:*` | Start here for latency/error alerts |
| `splunk-arcade` | `json`, `otel` | Only when alert service matches arcade apps |

**Service mapping:** APM `sf_service` often differs from container sourcetype. Use `service_aliases` in frontmatter or strip trailing `service`:

| APM / alert name | Use sourcetype |
|------------------|----------------|
| `payment`, `paymentservice` | `kube:container:payment` |
| `cart`, `cartservice` | `kube:container:cart` |
| `adservice`, `ad` | `kube:container:ad` |
| `emailservice`, `email` | `kube:container:email` |
| `currencyservice`, `currency` | `kube:container:currency` |
| `recommendationservice` | `kube:container:recommendation` |

If zero rows on container sourcetype, search **`httpevent`** with `_raw="*<service>*"` (e.g. `Payment request failed. Invalid token`).

**Live `kube:container:` sourcetypes (24h):** `frontend`, `payment`, `cart`, `ad`, `email`, `currency`, `recommendation`, `fraud-detection`, `product-catalog`, `product-reviews`, `accounting`, `kafka`, `llm`, `quote`, `traefik`, `postgresql`, `valkey-cart`, `registry`, `coredns`.

### IM (Infrastructure Monitoring)

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `kube:events`, `kube:container:*`, `auth_log`, `syslog` | Pod restarts, back-off, node/auth issues |

### RUM

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `httpevent`, `kube:container:frontend` | Backend correlated with RUM sessions |
| `splunk-arcade` | `json` | `deployment.environment`, `service.name`, `trace_id` in JSON |

### Synthetics

| Index | Sourcetypes | Notes |
|-------|-------------|-------|
| `splunk4rookies-workshop` | `httpevent`, `kube:container:*` | Target URL path + HTTP status during failure window |

## Field hints (from sample events)

| Sourcetype | Useful fields |
|------------|---------------|
| `kube:container:payment` | `_raw` stack traces and messages (`Payment request failed. Invalid token`); `source` pod path `/var/log/pods/default_payment-.../payment/0.log` |
| `httpevent` | Plain-text app messages in `_raw` (`payment went through`, error strings); `source=kubernetes` |
| `kube:events` | `_raw` pod/event text (`Back-off restarting failed container ...`) |

## Refreshing this catalog

From a facilitator machine with AMER Splunk MCP connected:

1. `splunk_get_metadata` with `type=sourcetypes`, `index=splunk4rookies-workshop`, `earliest_time=-24h`.
2. `splunk_run_query`: `index=splunk4rookies-workshop earliest=-1h | stats count by sourcetype | sort - count`.
3. Probe APM service names: `sourcetype="kube:container:<name>"` vs `httpevent _raw="*<name>*"`.
4. Update YAML frontmatter (`service_aliases`, `common_kube_containers`) and tables; run `pytest tests/part3/test_skill_tools.py`.

See [indexes.example.md](indexes.example.md) for a tenant-agnostic template.
