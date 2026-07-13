# troubleshoot-report — Reference

Optional detail for the **troubleshoot-report** skill. Keep [SKILL.md](SKILL.md) as the single entry point.

## Optional sections (expanded)

### Evidence collected

Bullet list of **which** systems were queried, not full payloads:

- Example: `o11y_search_alerts_or_incidents`, `o11y_get_apm_service_latency`, Splunk SPL search (name or purpose only), CLI command category.

Helps reviewers reproduce or extend the investigation later.

### Data gaps

Examples:

- Infrastructure tags missing on aggregated APM breakdowns (pod/node).
- Logs not indexed for the time range.
- No permission to run a specific API.

### Confidence

| Level | When to use |
|-------|-------------|
| **High** | Multiple independent signals agree (metrics + traces + logs). |
| **Medium** | Strong primary signal; gaps or circumstantial secondary signals. |
| **Low** | Hypothesis only, small sample, or conflicting data. |

## Mapping from Splunk Observability MCP (example)

When the toolchain includes O11y MCP alerts, typical mappings are:

| Report section | Example source fields |
|----------------|------------------------|
| Alert / incident | `detector`, `detectLabel`, `severity` |
| Identifiers | `incidentId`, `detectorId`, `eventId`, `id` |
| Timestamps | `anomaly_state_update_iso_8601_date_time` |
| Links | `link.url` on alert objects; `link.url` on APM service / trace objects |

Other tools should follow the same **report sections** using their native field names.
