# troubleshoot-synthetics-incidents — Reference

## Typical alert dimensions

Depends on detector; often includes **check name**, **journey**, **location**, **URL**, **HTTP status**, or **synthetic**-specific tags. Read **`customProperties`** from **`o11y_search_alerts_or_incidents`**.

## Metrics (examples — verify in org)

| Pattern | Use |
|---------|-----|
| `synthetics.duration.time.ms` | **Run / step duration** — regressions, tail latency |
| `synthetics.resource_request.count` | **Request volume** per check / phase |
| `synthetics.resource_request.size.bytes` | **Payload** size anomalies |

Discover with **`o11y_get_metric_names`**; dimensions with **`o11y_get_metric_metadata`**. Do **not** assume names unchanged across tenants.

## RUM overlap

If a **synthetic** and **RUM** both target the **same** app, compare **time windows** and **routes** — **synthetics** = **controlled** probes; **RUM** = **real users**. Use **RUM** (**troubleshoot-rum-incidents**) for user impact; **synthetics** for **proactive** failure.

## APM alignment

1. From the check definition or alert: **base URL**, **path**, **headers** → infer **service** (ingress, BFF, API).
2. Match **`deployment.environment`** / **`sf_environment`** to **APM** when tags exist on alerts or traces.
3. Use **trace IDs** in check output (if configured) to jump to **APM**.

## IM alignment

Use when failures are **regional**, **intermittent**, or tied to **specific probe locations** — correlate **target** **host**/**service** **CPU**, **errors**, **network** with **check** **location** and **timestamp**.

## Splunk logs

Same **UTC window** as failing runs. Prefer **structured** filters; see workspace **`AGENTS.md`** for **indexes** and **kube** / **httpevent** sourcetypes.

## Related skills

- **get-alerts-or-incidents**
- **troubleshoot-apm-incidents** · **troubleshoot-im-incidents** · **troubleshoot-rum-incidents**
- **troubleshoot-report**
