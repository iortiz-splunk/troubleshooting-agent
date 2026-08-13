# APM exemplar trace and span attribute reference

Supporting detail for **troubleshoot-apm-incidents**. Use after **o11y_get_apm_exemplar_traces** and **o11y_get_apm_trace_tool** to identify the failing component from span data.

---

## Exemplar types for trace pull

| Alert type | `exemplar_type` | Notes |
|------------|-----------------|-------|
| Error rate / 5xx | `err` | Sample traces that hit the error detector |
| Error rate (root cause) | `rc_err` | Prefer when available — points at downstream/origin error |
| Latency / P99 | `lat_buck_` | Trailing underscore required |
| General request sample | `req` | Use when errors are intermittent |

If both `err` and `rc_err` return `trace_id` values, analyze **`rc_err` first**, then confirm with `err`.

---

## Tool sequence (trace RCA)

1. **o11y_get_apm_exemplar_traces** — collect `trace_id` (and any inline tags) from the JSON.
2. **o11y_get_apm_trace_tool** — **required** when step 1 returns at least one `trace_id`. Pass `params.trace_id`; include `params.service_name` and `params.environment_name` when the tool schema requires them.
3. **Analyze spans** — do not stop at the exemplar list; open full trace detail before log search or final RCA.
4. Pull at most **two** full traces (one `rc_err`, one `err` or `lat_buck_`) — enough to confirm a pattern.

---

## Span tree walk (find root cause component)

1. Locate spans with **error status** — look for `error: true`, `otel.status_code: ERROR`, HTTP `4xx`/`5xx`, or `status.code` ≠ OK.
2. Prefer the **deepest error span** in the call chain (leaf or last downstream failure), not only the alerted service's entry span.
3. On that span, read **operation name** (`name`, `operation.name`) and **service** (`service.name`, `sf_service`).
4. Extract **human-readable failure text** from attributes (see table below) — quote short snippets in RCA; redact secrets.
5. Note **parent → child** path: e.g. `frontend → checkoutservice → payment` with error on `payment`.
6. If multiple traces show the same failing service + error message, mark RCA **Confirmed**; if only one exemplar, mark **Likely**.

---

## High-value span attributes (error RCA)

| Attribute / key | Use |
|-----------------|-----|
| `service.name` | Failing microservice / component |
| `operation.name` / span `name` | Handler, RPC, or DB operation |
| `exception.message`, `exception.type` | Exception class and message |
| `exception.stacktrace` | Class, method, line (when present) |
| `code.function`, `code.namespace`, `code.filepath`, `code.lineno` | Instrumented method location |
| `http.route`, `http.url`, `http.method`, `http.status_code` | HTTP handler and status |
| `rpc.system`, `rpc.service`, `rpc.method` | gRPC / RPC target |
| `db.system`, `db.name`, `db.statement` | Database dependency (truncate long SQL) |
| `messaging.system`, `messaging.destination` | Queue/topic failures |
| `error`, `error.message`, `message` | Generic error text on the span |
| `peer.service` | Downstream service name on client spans |

Also scan nested **tags**, **attributes**, and **process** blocks in the MCP JSON — field names vary slightly by instrumentation (OpenTelemetry, legacy SignalFx, auto-instrumentation).

---

## What to put in the investigation summary

Before **search-logs** or **troubleshoot-report**, include a short **Trace RCA** block:

- **Failing component:** service + operation (from span attributes)
- **Error evidence:** quoted `exception.message`, `http.status_code`, or similar (≤1 line)
- **Call path:** upstream → downstream to failing span
- **trace_id(s)** analyzed (for log correlation)

If exemplars return no traces or trace detail is empty, state **Trace RCA: no exemplar traces available** and continue with metrics + logs.

---

## Log correlation

Pass **`trace_id`** from exemplars or the error span into **search-logs** SPL (`trace_id="<id>"`) when Splunk MCP is connected.
