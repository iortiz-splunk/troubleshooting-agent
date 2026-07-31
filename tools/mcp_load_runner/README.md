# MCP Load Test Tool

Simulate **N concurrent Part 3 APM workshop participants** hitting Splunk MCP servers — **without an LLM**. Each virtual participant opens real `mcp-remote` sessions (same as the AI SRE Agent) and runs a scripted investigation.

**Default scenario (O11y only):** 4 tool calls per participant — alerts through errors (exemplar traces **off** by default).

**Full scenario (O11y + Splunk Cloud):** 5 tool calls — adds `splunk_run_query`.

O11y steps (always):

1. `o11y_search_alerts_or_incidents`
2. `o11y_get_apm_services`
3. `o11y_get_apm_service_latency`
4. `o11y_get_apm_service_errors_and_requests`

Optional O11y step (enable in UI or `--include-exemplar-traces`):

5. `o11y_get_apm_exemplar_traces` — SignalFx GraphQL; often **503 under concurrent load**. Use for 1-participant smoke tests only, or with 60–120s ramp-up.

Optional Splunk Cloud step:

6. `splunk_run_query` — searches `index=k8s-apps` for `_raw="*payment*"` by default

Defaults: APM service **`payment`**, environment **`sre-agent-workshop`**, exemplar type **`err`** when exemplars are enabled.

Use this to find how many simultaneous participants your MCP backends tolerate before latency spikes, throttling, or failures.

**Participant limit:** up to **200** concurrent virtual participants (`MAX_PARTICIPANTS`).

## Quick start

```bash
source .venv/bin/activate
pip install -e ".[loadtest]"

cd part3_agent && troubleshooting-agent mcp-doctor && cd ..

# UI (small runs)
streamlit run tools/mcp_load_runner/app.py

# CLI (EC2 / large runs)
ulimit -n 65535
mcp-load-test preflight --servers o11y
mcp-load-test run -n 50 --servers o11y --output-json results.json
```

## Prerequisites

- Repo `.env` configured (same as the workshop): `ENABLE_SPLUNK_O11Y`, `ENABLE_SPLUNK_CLOUD_MCP`, gateway URLs, tokens
- `npx` on PATH (for `mcp-remote`)
- Python 3.11+

Verify MCP connectivity first:

```bash
cd part3_agent
troubleshooting-agent mcp-doctor
```

## Install

From the repo root:

```bash
source .venv/bin/activate
pip install -e ".[loadtest]"
```

## Streamlit UI (laptop / small runs)

```bash
streamlit run tools/mcp_load_runner/app.py
```

1. Choose **MCP servers** in the sidebar (default: O11y only).
2. **Run MCP preflight** in the sidebar.
3. Set **Participants** (1–200). Warnings appear above 20 (laptop) and 50+ (EC2 recommended).
4. Use **Ramp-up** to stagger starts; `0` = everyone at once.
5. **Dry run (1 participant)** before large tests.

## Headless CLI (EC2 / stress tests)

Preferred for **50+ participants** (no Streamlit overhead):

```bash
ulimit -n 65535
npm install -g mcp-remote   # pre-warm; avoid 400 cold npx spawns

mcp-load-test run -n 200 --servers o11y --ramp-up 120 \
  --output-json results.json \
  --output-csv results.csv
```

Use `--servers o11y`, `--servers cloud`, or `--servers o11y,cloud`.

Options: `--service`, `--environment`, `--timeout`, `--stop-on-error`, `--skip-preflight`.

Exit code `2` if error rate exceeds 5%.

## EC2 sizing (200 participants, O11y + Splunk Cloud)

Each participant ≈ **2 `mcp-remote` processes** → **~400 subprocesses** at peak.

| Instance | vCPU | RAM | On-demand (~us-east-1 Linux) |
|----------|------|-----|------------------------------|
| **r7i.2xlarge** | 8 | 64 GB | ~**$0.53/hr** (~$4 for an 8-hour test day) |
| **r7i.4xlarge** (recommended) | 16 | 128 GB | ~**$1.06/hr** |
| **r7i.8xlarge** (headroom) | 32 | 256 GB | ~**$2.12/hr** |

Prices vary by region and change over time — check the [AWS EC2 pricing page](https://aws.amazon.com/ec2/pricing/on-demand/) before launching. EBS storage and data transfer are extra.

**Before a 200-participant run on EC2:**

```bash
ulimit -n 65535
npm install -g mcp-remote
# Same region as MCP gateway when possible
mcp-load-test run -n 1          # smoke
mcp-load-test run -n 200 --ramp-up 120 --output-json results.json
```

## Interpreting results

| Signal | Suggested threshold |
|--------|---------------------|
| Error rate | > 5% — gateway or capacity limit |
| p95 latency | > 30s — saturation |
| `rate_limit` errors | MCP throttling |
| `timeout` errors | Reduce load or increase timeout |

## Tests

```bash
pytest tests/mcp_load_runner/ -q -m "not mcp_integration"
pytest tests/mcp_load_runner/ -q -m mcp_integration  # requires live MCP
```

## Architecture

- Each participant = one `McpSessionManager` (separate `mcp-remote` subprocesses per integration)
- Tools invoked via LangChain wrappers (same path as the agent)
- Metrics: per-call latency, error classification, throughput, per-server breakdown
