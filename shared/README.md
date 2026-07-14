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

Auth uses `X-SF-REALM` + `X-SF-TOKEN` (not Splunk Cloud Bearer).

### Splunk Cloud / Enterprise MCP

| Variable | Description |
|----------|-------------|
| `ENABLE_SPLUNK_CLOUD_MCP` | Platform MCP (Bearer + tenant) |
| `ENABLE_SPLUNK_MCP` | On-prem Splunk Enterprise MCP |
| `MCP_NPX_COMMAND` | Default `npx` — runs `mcp-remote` over stdio |

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
| `ENABLE_SPLUNK_OTEL` | Splunk OTel APM for the agent process |
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
 Query: Investigate latency on Verification
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
2. Ensure `npx` is on your PATH.
3. Run `mcp-doctor` — expect `OK` and a list of `o11y_*` tools.
4. Test: `cd part1_agent && troubleshooting-agent chat "List APM environments"`.

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

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `doctor` fails | Ollama running / `OPENAI_*` correct / Azure deployment name |
| `mcp-doctor` fails | Gateway URL, realm, token; `npx` available |
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
