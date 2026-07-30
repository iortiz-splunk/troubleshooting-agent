# search-logs — SPL reference

Tenant-specific **indexes and sourcetypes** live in [indexes.md](indexes.md) (YAML frontmatter + tables). Read that catalog before calling `splunk_get_indexes`.

## Splunk Cloud MCP — `splunk_run_query`

**Arguments (flat — not nested `params`):**

| Field | Required | Example |
|-------|----------|---------|
| `query` | yes | `index=k8s-apps sourcetype="kube:container:payment" _raw="*error*" \| head 20` |
| `earliest_time` | no (default `-24h`) | `-1h`, `-30m`, `-40m` |
| `latest_time` | no (default `now`) | `now` |
| `row_limit` | no (default 100, max 1000) | `50` |

## Time formats (O11y vs Splunk)

**Do not copy O11y ISO timestamps into Splunk.** Alert fields like `anomaly_state_update_iso_8601_date_time` are valid for O11y `params.time_range` but **invalid** in Splunk SPL `earliest=`/`latest=`.

| Format | O11y MCP | Splunk MCP tool args | Splunk SPL `earliest=`/`latest=` |
|--------|----------|----------------------|----------------------------------|
| Relative | yes (`-1h`) | **yes (preferred)** | yes (`earliest=-1h latest=now`) |
| `now` | yes | yes | yes |
| ISO 8601 (`2026-07-30T14:17:20.000Z`) | yes | avoid | **no — fails validation / 0 rows** |
| Splunk datetime (`07/30/2026:14:17:20`) | no | avoid | works but prefer relative |

**Preferred:** set `earliest_time` / `latest_time` on the tool call only; leave time out of the SPL `query` string.

```json
{
  "query": "index=k8s-apps sourcetype=\"kube:container:payment\" | head 50",
  "earliest_time": "-1h",
  "latest_time": "now"
}
```

**Bad (causes Splunk error or silent 0 rows):**

```json
{
  "query": "index=k8s-apps earliest=2026-07-30T14:17:20.000Z latest=2026-07-30T14:57:20.000Z ...",
  "earliest_time": "2026-07-30T14:17:20.000Z",
  "latest_time": "2026-07-30T14:57:20.000Z"
}
```

For a recent alert, use `-1h`/`now` or `-40m`/`now` instead of converting the alert ISO time.

**Response:**

```json
{
  "results": [
    {
      "_raw": "Payment request failed. Invalid token. app.loyalty.level=gold",
      "_time": "2026-07-29 21:51:01.401 UTC",
      "sourcetype": "httpevent",
      "source": "kubernetes",
      "host": "k3d-shw-2cb1-cluster-agent-0",
      "index": "k8s-apps"
    }
  ],
  "total_rows": 1,
  "truncated": false
}
```

Zero hits: `{"results":[],"total_rows":0}` — not a failure; widen sourcetype or search `httpevent`.

**Discovery fallback:** `splunk_get_metadata` with `{"type": "sourcetypes", "index": "k8s-apps", "earliest_time": "-24h"}`.

## Service name → sourcetype (workshop tenant)

APM `sf_service` may not match container sourcetype literally:

| Alert / APM name | Search first |
|------------------|--------------|
| `payment`, `paymentservice` | `sourcetype="kube:container:payment"` |
| `cart`, `cartservice` | `sourcetype="kube:container:cart"` |
| `adservice` | `sourcetype="kube:container:ad"` |
| No kube match (e.g. `Verification`) | `sourcetype=httpevent _raw="*Verification*"` |

See `service_aliases` in [indexes.md](indexes.md) frontmatter.

## Common field names by data source

| Data source | Fields to try |
|-------------|----------------|
| Kubernetes container logs | `_raw` (stack/message text), `source` (pod log path), `sourcetype` |
| JSON app logs | `service`, `service.name`, `message`, `trace_id`, `severity` |
| Access / HTTP | `http.resp.status`, `http.resp.took_ms` in structured `_raw` |
| Splunk Observability correlation | `trace_id` from **`o11y_get_apm_exemplar_traces`** |

## Product-specific starting points

| Product | Log focus |
|---------|-----------|
| **APM** | Errors for mapped container sourcetype + `httpevent`; trace IDs from exemplars |
| **IM** | Pod/node from alert; K8s events (`kube:events`) |
| **RUM** | Backend logs in `httpevent` / `kube:container:frontend` |
| **Synthetics** | Gateway/app `httpevent` for target path + 5xx |

## Performance tips

- Always set **`earliest`** / **`latest`** (or `-30m` minimum).
- Prefer **`index=<name>`** over `index=*`.
- Use **`head 50`** or **`stats`** before returning large raw event lists.
- At most **two** `splunk_run_query` calls per investigation.
