# search-logs — SPL reference

Tenant-specific **indexes and sourcetypes** live in [indexes.md](indexes.md) (YAML frontmatter + tables). Read that catalog before calling `splunk_get_indexes`.

## Common field names by data source

| Data source | Fields to try |
|-------------|----------------|
| Kubernetes container logs | `k8s.namespace.name`, `k8s.pod.name`, `k8s.container.name`, `k8s.workload.name`, `kubernetes.labels.app` |
| JSON app logs | `service`, `service.name`, `app`, `level`, `message`, `msg`, `trace_id`, `span_id` |
| Access / HTTP | `status`, `http_status`, `method`, `uri`, `path`, `response_time`, `duration` |
| Splunk Observability correlation | `deployment.environment`, `environment`, `sf_service` (if forwarded in logs) |

## Product-specific starting points

| Product | Log focus |
|---------|-----------|
| **APM** | Errors and slow paths for **`sf_service`** + **`sf_environment`**; trace IDs from **`o11y_get_apm_exemplar_traces`** → search `trace_id` or `traceId` in logs |
| **IM** | Pod/node/host from alert **`customProperties`**; K8s events (`reason`, `message`) if indexed |
| **RUM** | Backend/API logs for services tied to **`deployment.environment`** / **`app`** |
| **Synthetics** | Gateway/app logs for **target URL**, **path**, **5xx** during check failures |

## Performance tips

- Always set **`earliest`** / **`latest`** (or `-30m` minimum).
- Prefer **`index=<name>`** over `index=*`.
- Use **`head 50`** or **`stats`** before returning large raw event lists.
- If `splunk_run_query` fails validation, remove destructive commands and retry with a simpler search.

## MCP tool parameter notes

Tool schemas vary by server version. Pass the SPL string in the field required by **`splunk_run_query`** (often `query`, `search`, or `spl`). Read the tool description in your session if a call fails validation.
