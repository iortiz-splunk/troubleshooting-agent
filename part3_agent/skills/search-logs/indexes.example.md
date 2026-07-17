---
tenant: your-tenant-name
gateway_region: region-xxxxx
discovered_at: "YYYY-MM-DD"
default_index: your-primary-app-index
do_not_use:
  - index: _internal
    reason: Splunk platform logs only
  - index: _introspection
    reason: Splunk introspection metrics only
products:
  apm:
    primary_index: your-primary-app-index
    secondary_indexes: []
    sourcetypes:
      - httpevent
      - "kube:container:*"
      - json
    notes:
      - "Map sf_service to kube:container:<lowercase-hyphenated> when present."
      - "Fall back to httpevent/json text search when no matching container sourcetype."
    common_kube_containers: []
    example_spl: |
      index=your-primary-app-index earliest=-1h latest=now
      (sourcetype="kube:container:your-service" OR sourcetype=httpevent)
      (severity=error OR http.resp.status>=400 OR _raw="*error*")
      | head 50
  im:
    primary_index: your-primary-app-index
    sourcetypes:
      - kube:events
      - "kube:container:*"
    notes:
      - "Search kube:events for pod restart and scheduling failures."
    example_spl: |
      index=your-primary-app-index earliest=-1h latest=now
      sourcetype=kube:events _raw="*Failed*"
      | head 50
  rum:
    primary_index: your-primary-app-index
    sourcetypes:
      - httpevent
      - "kube:container:frontend"
    notes:
      - "Scope to RUM anomaly window and backend service from session tags."
    example_spl: |
      index=your-primary-app-index earliest=-1h latest=now
      sourcetype=httpevent http.resp.status>=400
      | head 50
  synthetics:
    primary_index: your-primary-app-index
    sourcetypes:
      - httpevent
      - "kube:container:*"
    notes:
      - "Filter by target path/host and 5xx during synthetic check failures."
    example_spl: |
      index=your-primary-app-index earliest=-1h latest=now
      sourcetype=httpevent status>=500
      | head 50
---

# Log index catalog — template

Copy to `indexes.md` in the same directory and fill in from your Splunk MCP tenant.

## Setup

1. Connect Splunk Cloud MCP for your workshop tenant.
2. Run discovery queries (see **Refreshing** in `indexes.md`).
3. Save as `part3_agent/skills/search-logs/indexes.md` (gitignored or committed per workshop policy).
4. Verify: `pytest tests/part3/test_skill_tools.py -k catalog`

## YAML frontmatter fields

| Field | Purpose |
|-------|---------|
| `default_index` | First index in SPL when product has no override |
| `do_not_use` | Indexes the agent must not search for app issues |
| `products.<type>.primary_index` | Index for APM / IM / RUM / Synthetics |
| `products.<type>.sourcetypes` | Preferred sourcetypes (supports `*` wildcards in prose only) |
| `products.<type>.example_spl` | Injected into investigate prompts |

The Part 3 graph loads YAML frontmatter via `load_log_index_catalog()` and injects the slice for the alert's `product_type`.
