# Shared integrations handbook

Participants: you usually **do not edit** code in `shared/workshop_shared/`. Use this doc to configure credentials and verify integrations before running a workshop part.

## Verify setup

Run `troubleshooting-agent` from inside `part1_agent/`, `part2_agent/`, or `part3_agent/`:

```bash
cd part1_agent
troubleshooting-agent doctor          # LLM connectivity
troubleshooting-agent mcp-doctor      # Splunk MCP servers + tool list
troubleshooting-agent slack-doctor    # Slack bot + alerts channel
```

The same commands work in each part directory; only the agent behavior changes.

## Environment variables

Copy [`.env.example`](../.env.example) to `.env` at the repo root.

### LLM

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `ollama` (default), `openai`, or `azure_openai` |
| `OLLAMA_BASE_URL` | Default `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Default `qwen2.5-coder:7b` |
| `OPENAI_API_KEY` | API key for OpenAI-compatible proxy |
| `OPENAI_BASE_URL` | Base URL including `/v1` when required |
| `OPENAI_MODEL_NAME` | Model name routed by proxy |
| `AZURE_OPENAI_*` | Endpoint, key, deployment, API version |

Provider auto-detection: if `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set, `openai` is used unless `LLM_PROVIDER` overrides.

### Splunk Observability MCP (o11y_* tools)

| Variable | Description |
|----------|-------------|
| `ENABLE_SPLUNK_O11Y` | `true` to enable |
| `SPLUNK_O11Y_GATEWAY_URL` | Splunk Cloud MCP gateway URL |
| `SPLUNK_O11Y_REALM` | Observability realm (e.g. `us1`) |
| `SPLUNK_O11Y_API_TOKEN` | Observability API token (`X-SF-TOKEN`) |
| `SPLUNK_O11Y_TOOL_PREFIX` | Default `o11y_` |
| `SPLUNK_O11Y_ENVIRONMENT` | Default APM environment for `o11y_get_apm_*` when alert/metadata omit `sf_environment` (default: `sre-agent-workshop`) |
| `SPLUNK_SEARCH_INDEX` | Default Splunk index for `splunk_run_query` (default: `splunk4rookies-workshop`) |

Auth uses `X-SF-REALM` + `X-SF-TOKEN` (not Splunk Cloud Bearer).

### Splunk Cloud / Enterprise MCP

| Variable | Description |
|----------|-------------|
| `ENABLE_SPLUNK_CLOUD_MCP` | Platform MCP (Bearer + tenant) |
| `ENABLE_SPLUNK_MCP` | On-prem Splunk Enterprise MCP |
| `MCP_NPX_COMMAND` | Default `npx` — runs `mcp-remote` over stdio |
| `MCP_TLS_INSECURE` | Set `true` to pass `NODE_TLS_REJECT_UNAUTHORIZED=0` to mcp-remote (staging/self-signed certs only) |
| `MCP_TLS_CA_CERTS` | Path to a CA bundle for mcp-remote (`NODE_EXTRA_CA_CERTS`; preferred over insecure) |

**Self-signed TLS:** Splunk Cloud MCP on staging often uses a self-signed certificate. mcp-remote runs under Node.js, so the agent passes TLS settings via subprocess env (same as Cursor’s `"env"` block on the MCP server). For a quick workshop workaround, add `MCP_TLS_INSECURE=true` to `.env`. For production, use `MCP_TLS_CA_CERTS` pointing at your CA PEM instead.

### Slack demo

| Variable | Description |
|----------|-------------|
| `ENABLE_SLACK` | `true` to enable Socket Mode listener |
| `SLACK_BOT_TOKEN` | `xoxb-...` |
| `SLACK_APP_TOKEN` | `xapp-...` (Socket Mode) |
| `SLACK_SIGNING_SECRET` | App signing secret |
| `SLACK_ALERTS_CHANNEL_NAME` | Channel for Observability alerts |
| `SLACK_ALERTS_CHANNEL_ID` | Optional if name lookup fails |

Run `slack-listen` on any workshop part after `slack-doctor` passes. Resolved/cleared alerts are ignored automatically.

### Observability

| Variable | Description |
|----------|-------------|
| `AGENT_LOG_TRACE` | Human-readable investigation logs in terminal (default: on) |
| `AGENT_LOG_DEBUG` | Verbose MCP tool-arg previews in terminal |
| `AGENT_LOG_DIR` | Per-investigation JSONL files (default: `shared/logs/investigations`; empty to disable) |
| `LOG_FORMAT` | `text` (default) or `json` for log lines |
| `ENABLE_SPLUNK_OTEL` | Export agent traces/metrics via OTLP to a local OpenTelemetry Collector |
| `OTEL_SERVICE_NAME` | Service name on exported spans (default: `troubleshooting-agent`) |
| `OTEL_COLLECTOR_ENDPOINT` | OTLP/HTTP base URL for the collector (default: `http://localhost:4318`) |
| `OTEL_RESOURCE_ATTRIBUTES` | Optional comma-separated resource attrs, e.g. `deployment.environment=demo` |

Agent telemetry goes to the **local collector** only. The collector (see workshop docs) holds the Splunk ingest token and realm — the agent does not need `SPLUNK_ACCESS_TOKEN` or `SPLUNK_O11Y_REALM` for export.
| `ENABLE_GALILEO` | Galileo session tracing |
| `GALILEO_API_KEY` | Galileo API key |
| `GALILEO_CONSOLE_URL` | Your Galileo console URL (required) |
| `GALILEO_PROJECT` | Project name |
| `GALILEO_LOG_STREAM` | Log stream name |

Galileo sessions are named from Observability **`eventId`** plus the active workshop part (e.g. `slack-alert-HNNiTkcA0AA | part2_agent`).

### What you see in the terminal

With `AGENT_LOG_TRACE=true` (default), every part prints a structured trace:

```text
══════════════════════════════════════════════════════════════
 Investigation  chat:abc123  |  part2  |  cli
──────────────────────────────────────────────────────────────
 Query: Investigate latency on payment in the sre-agent-workshop environment
 Skill: latency-spike
 LLM: ollama  |  MCP tools available: 12
══════════════════════════════════════════════════════════════
[1] Skill loaded: latency-spike
[2] LLM turn 1 — calling tools: o11y_search_alerts_or_incidents
[3] MCP o11y_search_alerts_or_incidents — OK (2.1 KB) | alerts=1
[4] LLM turn 2 — composing final response (420 chars)
──────────────────────────────────────────────────────────────
 Agent response
──────────────────────────────────────────────────────────────
- Alert confirmed ...
══════════════════════════════════════════════════════════════
```

Part 3 adds `Graph ▸ identify (start)` lines between ReAct steps. The same events are written to `shared/logs/investigations/<id>.jsonl` for facilitators.

When trace is on, `troubleshooting-agent chat` prints the response in the log block (not duplicated below). Set `AGENT_LOG_TRACE=false` for response-only output.

## Splunk MCP setup

1. Enable the integration(s) in `.env`.
2. Ensure Node.js **20** and `npx` are on your PATH (`mcp-remote` requires Node 18+; Ubuntu `apt install nodejs` often ships Node 12). Facilitators: run `scripts/workshop-instance-setup.sh` on each EC2 instance.
3. Run `mcp-doctor` — expect `OK` and a list of `o11y_*` tools.
4. Test: `cd part1_agent && troubleshooting-agent chat "List APM environments"`.

**MCP URL paths:** Set `SPLUNK_CLOUD_MCP_URL` and `SPLUNK_O11Y_GATEWAY_URL` to the direct MCP server (`https://mcp-<instance>.stg.splunkcloud.com:8089/services/mcp`). Host-only values get `:8089/services/mcp` appended. If o11y still uses legacy `region-*.api.scs.splunk.com`, the agent reuses the Cloud MCP URL automatically.

MCP tools expect a `params` object. For time windows use:

```json
{"start": "-1h", "stop": "now"}
```

not a bare string like `-1h`.

## Slack demo setup

1. Create a Slack app with **Socket Mode**, **Bot Token**, and **App Token**.
2. Invite the bot to your Observability alerts channel.
3. Set Slack variables in `.env` and run `slack-doctor`.
4. `cd part3_agent && troubleshooting-agent slack-listen` and post/trigger an alert.

The listener refetches thin bot messages, skips resolved alerts, enriches context via MCP (`eventId`), and replies in the alert thread.

## Facilitator capacity testing

Before a large workshop, estimate how many simultaneous participants your MCP backends can handle:

```bash
pip install -e ".[loadtest]"
streamlit run tools/mcp_load_runner/app.py   # UI — check O11y in sidebar, run preflight
mcp-load-test preflight --servers o11y
mcp-load-test run -n 200 --servers o11y --ramp-up 120 --output-json results.json   # EC2 headless
```

The load runner simulates **N concurrent Part 3 APM investigations** (scripted MCP tool calls, no LLM). For **200 participants**, use an **r7i.4xlarge** (128 GB) or larger EC2 instance with `ulimit -n 65535`. See [`tools/mcp_load_runner/README.md`](../tools/mcp_load_runner/README.md) for sizing and AWS cost estimates.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `doctor` fails | Ollama running / `OPENAI_*` correct / Azure deployment name |
| `mcp-doctor` fails | Gateway URL, realm, token; `npx` available; read `→` hint lines under each FAILED server |
| `Connection closed` on MCP | URL wrong, token expired, or missing `SPLUNK_CLOUD_MCP_TENANT` — `mcp-doctor` prints URL, credential status, HTTP probe, and mcp-remote stderr |
| No o11y data in answers | `mcp-doctor` lists tools; model uses `params` object |
| Slack listener silent | `slack-doctor`; channel name; alert is not resolved |
| Galileo session name wrong | MCP pre-resolve sets `event_id` from `eventId` |

## Package layout

```text
shared/workshop_shared/
  config.py          # Settings from .env
  mcp/               # MCP bridge, session, gateway
  slack/             # listener, messages, alert_resolve
  llm/               # Ollama, OpenAI, Azure factories
  observability/     # logging trace, OTel, Galileo
  agent_registry.py  # wires active part's run_chat for Slack
shared/logs/
  investigations/    # JSONL trace files (auto-created; gitignored)
```
