# Troubleshooting Agent

AI agent for troubleshooting applications and systems. It uses **Ollama** (local), an **OpenAI-compatible API** (e.g. LiteLLM proxy), or **Azure OpenAI** via LangChain/LangGraph and can connect to **Splunk Observability** and **Splunk Enterprise MCP** servers (same transport as Cursor: `mcp-remote` over stdio).

**Quick start (Splunk + LiteLLM):** copy [`.env.example`](.env.example) → set `OPENAI_*` and Splunk o11y vars → `doctor` → `mcp-doctor` → `chat`.

**Quick start (local Ollama):** [New machine setup](#new-machine-setup) → [Splunk MCP setup](#splunk-mcp-setup) → `mcp-doctor` → [Test MCP with the agent](#test-mcp-with-the-agent).

## Contents

- [What you need](#what-you-need)
- [How it works](#how-it-works) — agent loop, components, data flow
- [Project structure](#project-structure)
- [LLM providers](#llm-providers) — Ollama, OpenAI-compatible, Azure
- [New machine setup](#new-machine-setup) (Ollama + Python)
- [OpenAI-compatible API](#openai-compatible-api-optional) — LiteLLM proxy, `OPENAI_*` env vars
- [Azure OpenAI](#azure-openai-optional) — native Azure client
- [Splunk MCP setup](#splunk-mcp-setup) (configure, test, example chats)
- [Slack demo setup](#slack-demo-setup) (alert channel → auto-investigate in thread)
- [Usage reference](#usage-reference)
- [Development](#development)
- [Troubleshooting setup issues](#troubleshooting-setup-issues)

## What you need

| Requirement | Notes |
|-------------|--------|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) or Homebrew on macOS |
| LLM | **Ollama**, **OpenAI-compatible** (`OPENAI_*`), or **Azure OpenAI** — see [LLM providers](#llm-providers) |
| Ollama + model | When using Ollama locally: [install Ollama](https://ollama.com) and `qwen2.5-coder:7b` |
| OpenAI-compatible | When using LiteLLM proxy: `OPENAI_API_KEY` + `OPENAI_BASE_URL` (auto-selected; no Ollama needed) |
| Azure OpenAI | When using native Azure client: endpoint, key, deployment name, API version |
| Node.js `npx` | Required when Splunk MCP integrations are enabled (runs `mcp-remote`) |

Dependencies are declared in [`pyproject.toml`](pyproject.toml). There is no separate `requirements.txt`; install the project in editable mode and pip (or uv) resolves everything from that file.

---

## How it works

The troubleshooting agent is a **tool-calling LLM loop** built with [LangGraph](https://langchain-ai.github.io/langgraph/). You ask a question via the CLI; the model decides whether to call Splunk Observability (or other) tools, reads the results, and returns a summarized answer.

### Request flow

```mermaid
flowchart TB
  subgraph cli [CLI]
    chat[troubleshoot-agent chat]
    doctor[troubleshoot-agent doctor]
    mcpdoc[troubleshoot-agent mcp-doctor]
  end

  subgraph config [Configuration]
    env[".env / Settings"]
  end

  subgraph llm [LLM layer]
    factory[llm/factory.py]
    ollama[ChatOllama]
    openai[ChatOpenAI]
    azure[AzureChatOpenAI]
  end

  subgraph agent [Agent loop - LangGraph]
    graph[agent/graph.py]
    tools_node[ToolNode]
    parse[tool_calls.py]
  end

  subgraph mcp [MCP layer]
    session[McpSessionManager]
    remote[mcp-remote subprocess]
    bridge[mcp/bridge.py]
    o11y_tools[o11y_* tools]
  end

  chat --> env
  doctor --> env
  mcpdoc --> env
  chat --> session
  session --> remote
  remote --> bridge
  bridge --> o11y_tools
  chat --> factory
  factory --> ollama
  factory --> openai
  factory --> azure
  chat --> graph
  graph --> factory
  graph --> parse
  graph --> tools_node
  tools_node --> o11y_tools
  tools_node --> graph
```

### Agent loop (ReAct-style)

Each `chat` invocation runs a short LangGraph loop:

1. **User message** enters the graph as a `HumanMessage`.
2. **Agent node** calls the LLM with the system prompt and bound tools.
3. If the model returns **tool calls**, the **tools node** executes them (e.g. `o11y_get_apm_environments`).
4. **Tool results** are appended as `ToolMessage`s and the agent node runs again.
5. The loop ends when the model replies with a normal text answer (no more tool calls).
6. **Runner** picks the best final assistant message and prints it.

On the first turn, when MCP tools are available, the agent requires at least one tool call so the model fetches live data instead of only describing what it would do.

Some models (especially local Ollama) emit tool calls as JSON text instead of structured fields. `agent/tool_calls.py` parses that JSON, normalizes o11y `params` wrappers, and feeds proper `tool_calls` into the graph.

### Major components

| Component | Role |
|-----------|------|
| **`cli.py`** | Typer commands: `doctor` (LLM health), `mcp-doctor` (MCP connectivity), `chat` (run agent) |
| **`config.py`** | Loads `.env`; validates Splunk/MCP credentials; auto-detects LLM provider |
| **`llm/factory.py`** | Builds `ChatOllama`, `ChatOpenAI`, or `AzureChatOpenAI` from settings |
| **`llm/invoke_health.py`** | Probes remote LLMs with a minimal `ping` message (`doctor`) |
| **`agent/graph.py`** | LangGraph state machine: `agent` ↔ `tools` |
| **`agent/runner.py`** | Wires LLM + tools + MCP session; extracts final response |
| **`agent/tool_calls.py`** | Parses JSON tool calls; wraps flat args into MCP `params` |
| **`prompts/system.py`** | SRE/troubleshooting system prompt and o11y usage rules |
| **`mcp/gateway.py`** | Builds `mcp-remote` argv (headers for o11y, Cloud, Enterprise) |
| **`mcp/session.py`** | Keeps MCP subprocess alive for the duration of a `chat` run |
| **`mcp/bridge.py`** | Lists MCP tools; converts them to LangChain `StructuredTool`s |
| **`tools/base.py`** | Tool registry (built-ins + MCP tools passed at runtime) |

### MCP transport

Splunk tools are not HTTP calls from Python directly. The agent spawns **`npx mcp-remote`** (same pattern as Cursor MCP), which speaks MCP over stdio to the Splunk Cloud gateway. Auth headers (`X-SF-REALM`, `X-SF-TOKEN` for o11y) are passed on the `mcp-remote` command line. `McpSessionManager` holds that subprocess open so multiple tool calls in one chat reuse the same connection.

---

## Project structure

```
troubleshooting-agent/
├── pyproject.toml              # Dependencies and CLI entry point
├── .env.example                # Environment template (copy to .env)
├── README.md
├── src/troubleshooting_agent/
│   ├── cli.py                  # doctor | mcp-doctor | slack-* | chat
│   ├── config.py               # Settings, validation, LLM auto-detect
│   ├── agent/
│   │   ├── graph.py            # LangGraph tool-calling loop
│   │   ├── runner.py           # Async chat orchestration + response formatting
│   │   └── tool_calls.py       # JSON tool-call parsing and arg normalization
│   ├── llm/
│   │   ├── factory.py          # build_llm() — provider switch
│   │   ├── invoke_health.py    # Remote LLM health probe
│   │   └── ollama.py           # Ollama-specific health check
│   ├── mcp/
│   │   ├── gateway.py          # mcp-remote StdioServerParameters per integration
│   │   ├── connect.py          # MCP session context helper
│   │   ├── session.py          # McpSessionManager lifecycle
│   │   └── bridge.py           # MCP → LangChain tools, mcp-doctor checks
│   ├── prompts/
│   │   └── system.py           # System prompt for the agent
│   ├── slack/
│   │   ├── listener.py         # Socket Mode: alert → agent → thread reply
│   │   ├── doctor.py           # slack-doctor connectivity check
│   │   └── channels.py         # Resolve #splunk-observability-alerts-1 → ID
│   └── tools/
│       ├── base.py             # get_tools() registry
│       ├── builtin.py          # Always-on helper tools
│       └── stubs/              # Splunk o11y / Cloud / Enterprise loaders
└── tests/                      # Unit tests (+ optional integration markers)
```

---

## LLM providers

Three backends are supported. You only configure one at a time.

| Provider | When to use | Key env vars |
|----------|-------------|--------------|
| **`openai`** | Splunk LiteLLM proxy, OpenAI.com, any OpenAI-compatible API | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, optional `OPENAI_MODEL_NAME` |
| **`ollama`** | Local development, no API key | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| **`azure_openai`** | Direct Azure OpenAI resource with deployment + API version | `AZURE_OPENAI_*` (four vars) |

### Auto-detection

If `LLM_PROVIDER` is **not set**, the app picks a provider automatically:

1. `OPENAI_API_KEY` + `OPENAI_BASE_URL` present → **`openai`**
2. Else all four `AZURE_OPENAI_*` vars present → **`azure_openai`**
3. Else → **`ollama`**

Set `LLM_PROVIDER` explicitly to override (e.g. `LLM_PROVIDER=ollama` even when `OPENAI_*` vars exist).

Shared optional setting: `LLM_TEMPERATURE` (alias: `OLLAMA_TEMPERATURE`).

---

## New machine setup

Follow these steps on a fresh clone. **Skip steps 1–2** if you use a remote LLM ([OpenAI-compatible](#openai-compatible-api-optional) or [Azure](#azure-openai-optional)) instead of local Ollama.

### 1. Install Ollama (local LLM only)

Ollama runs the language model on your machine. Install it for your OS, then keep the Ollama app or service running in the background.

#### macOS (Homebrew)

```bash
brew install ollama
```

Start Ollama (runs the API on port 11434):

```bash
# Foreground (good for first-time testing)
ollama serve

# Or start the menu bar app from Applications after: brew install --cask ollama
```

#### Windows

1. Download the installer from [https://ollama.com/download](https://ollama.com/download).
2. Run the installer and finish the setup wizard.
3. Ollama should start automatically and appear in the system tray.

Alternatively, with [winget](https://learn.microsoft.com/en-us/windows/package-manager/winget/):

```powershell
winget install Ollama.Ollama
```

Verify the API is up (PowerShell or Command Prompt):

```powershell
curl http://127.0.0.1:11434/api/tags
```

### 2. Download the Qwen 2.5 Coder model

This project is configured for **Qwen 2.5 Coder** (7B). The download is several GB and only needs to be done once per machine.

```bash
ollama pull qwen2.5-coder:7b
```

Confirm it appears in the model list:

```bash
ollama list
```

You should see `qwen2.5-coder:7b` (or a similar tag). Quick sanity check:

```bash
ollama run qwen2.5-coder:7b "Say hello in one sentence."
```

### 3. Install Python dependencies

Clone or open this repository, then choose **one** of the install methods below.

#### Configure environment

```bash
cd troubleshooting-agent
cp .env.example .env
```

The example `.env` already points at `qwen2.5-coder:7b`. Change `OLLAMA_BASE_URL` only if Ollama is not on `http://127.0.0.1:11434`.

#### Option A — pip and virtualenv (works on Windows, macOS, Linux)

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat
```

Install the app and dev tools (pytest, ruff, mypy):

```bash
pip install -e ".[dev]"
```

#### Option B — uv (faster, optional)

If you have [uv](https://docs.astral.sh/uv/) installed:

```bash
uv sync --extra dev
```

Use `uv run troubleshoot-agent ...` for commands without activating `.venv`.

### 4. Verify the LLM

```bash
troubleshoot-agent doctor
```

**Ollama** expected output:

```text
LLM provider: ollama
Ollama: OK
Available models:
  - qwen2.5-coder:7b
Ready.
```

**OpenAI-compatible** (LiteLLM) expected output:

```text
LLM provider: openai
Base URL: https://lite-llm-proxy.splunko11y.com/v1
Model: gpt-4.1-mini
OpenAI-compatible LLM: OK
Ready.
```

If Ollama is selected but the model is missing, run `ollama pull qwen2.5-coder:7b`. If you intended to use LiteLLM, ensure `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set in `.env` (provider auto-detects to `openai`).

### 5. Run the agent (without Splunk MCP)

Without MCP, the agent answers from the LLM only (no live Observability data):

```bash
troubleshoot-agent chat "Why might service X return 503?"
```

With uv, without activating the venv:

```bash
uv run troubleshoot-agent chat "Why might service X return 503?"
```

---

## OpenAI-compatible API (optional)

Use a **LiteLLM proxy**, OpenAI.com, or any OpenAI-compatible endpoint. Set `OPENAI_API_KEY` and `OPENAI_BASE_URL` — you do **not** need `LLM_PROVIDER=openai` unless you want to force it (auto-detected when those vars are present).

### Configure `.env`

```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://lite-llm-proxy.splunko11y.com/v1
OPENAI_MODEL_NAME=gpt-4.1-mini
# LLM_PROVIDER=openai   # optional; auto-detected from OPENAI_* vars above
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | API key for the proxy or OpenAI service |
| `OPENAI_BASE_URL` | Yes | Base URL including `/v1` suffix when required by your proxy |
| `OPENAI_MODEL_NAME` | No | Model routed by the proxy (default: `gpt-4.1-mini`) |

Optional: `LLM_TEMPERATURE=0.2`

### Test

```bash
pip install -e ".[dev]"
troubleshoot-agent doctor
```

Expected:

```text
LLM provider: openai
Base URL: https://lite-llm-proxy.splunko11y.com/v1
Model: gpt-4.1-mini
OpenAI-compatible LLM: OK
Ready.
```

Then with Splunk MCP (if configured):

```bash
troubleshoot-agent mcp-doctor
troubleshoot-agent chat "List APM environments"
```

This matches the `ChatOpenAI` + `OPENAI_API_KEY` / `OPENAI_BASE_URL` pattern used in other Splunk agent projects.

---

## Azure OpenAI (optional)

Use the **native Azure OpenAI client** when you have an Azure resource with explicit deployment and API version. For Splunk’s LiteLLM proxy, prefer [OpenAI-compatible API](#openai-compatible-api-optional) instead.

### When to use Azure vs Ollama

| | Ollama (default) | Azure OpenAI |
|--|----------------|--------------|
| Setup | Local install + model pull | Azure endpoint + API key + deployment |
| `LLM_PROVIDER` | `ollama` (or unset) | `azure_openai` |
| Tool calling | Works; may need JSON parsing fallback | Native tool calls (recommended for MCP) |
| `doctor` check | Lists local Ollama models | Probes deployment with a test message |

### Configure `.env`

```bash
LLM_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-10-21
```

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Resource URL from Azure portal (trailing slash optional) |
| `AZURE_OPENAI_API_KEY` | API key for the resource (never commit) |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | **Deployment** name in Azure — not the underlying model name |
| `AZURE_OPENAI_API_VERSION` | API version your resource supports (e.g. `2024-10-21`) |

Optional: `LLM_TEMPERATURE=0.2` (also accepts legacy `OLLAMA_TEMPERATURE`).

### Test Azure OpenAI

```bash
pip install -e ".[dev]"
troubleshoot-agent doctor
```

Expected:

```text
LLM provider: azure_openai
Endpoint: https://your-resource.openai.azure.com/
Deployment: your-deployment-name
Azure OpenAI: OK
Ready.
```

Then with Splunk MCP (if configured):

```bash
troubleshoot-agent mcp-doctor
troubleshoot-agent chat "List APM environments"
```

### Switch back to Ollama

```bash
LLM_PROVIDER=ollama
# or remove LLM_PROVIDER and use defaults
```

---

### 6. Splunk MCP (optional, recommended)

To query **live** Observability alerts, APM, traces, and metrics, enable at least one Splunk MCP integration in `.env`. The agent uses the same transport as **Cursor**: `npx mcp-remote` over stdio with HTTP headers for auth.

**Quick path:** if MCP already works in Cursor, copy the same URL and headers into `.env` (see [Splunk MCP setup](#splunk-mcp-setup) below), run `mcp-doctor`, then try the [example chats](#test-mcp-with-the-agent).

---

## Splunk MCP setup

### Which integration do I need?

| Integration | Enable flag | Use for | Auth |
|-------------|-------------|---------|------|
| **Splunk Observability Cloud** | `ENABLE_SPLUNK_O11Y=true` | Alerts, APM, traces, metrics (`o11y_*` tools) | `X-SF-REALM` + `X-SF-TOKEN` (Observability API token) |
| **Splunk Cloud MCP** | `ENABLE_SPLUNK_CLOUD_MCP=true` | Splunk Cloud platform / logs (non-o11y MCP tools) | `Authorization: Bearer` + `splunk_tenant` |
| **Splunk Enterprise MCP** | `ENABLE_SPLUNK_MCP=true` | On-prem Splunk MCP endpoint | `Authorization: Bearer` |

Most troubleshooting workflows start with **Observability only** (`ENABLE_SPLUNK_O11Y`). Do not put Splunk Cloud Bearer/tenant on the o11y integration — that is a separate server with different credentials.

You can enable more than one at a time (for example o11y + Enterprise).

### Prerequisites for MCP

| Requirement | Why |
|-------------|-----|
| Node.js + `npx` on your PATH | Runs `mcp-remote` (same as Cursor) |
| Network access to the MCP gateway URL | Usually Splunk Cloud `*.api.scs.splunk.com` |
| Valid tokens in `.env` | Never commit `.env`; it is gitignored |

Optional: `MCP_NPX_COMMAND=npx` in `.env` if `npx` is not the default command name.

### Step 1 — Copy settings from Cursor (easiest)

If Splunk MCP already works in Cursor, mirror that config in `.env`.

1. Open Cursor MCP settings (or your `mcp.json`).
2. Find the server entry for Observability (often named like `o11y-mcp-server` or similar).
3. Note:
   - **URL** → `SPLUNK_O11Y_GATEWAY_URL`
   - **Header `X-SF-REALM`** → `SPLUNK_O11Y_REALM`
   - **Header `X-SF-TOKEN`** → `SPLUNK_O11Y_API_TOKEN`

Example Cursor-style server block (values are placeholders):

```json
{
  "command": "npx",
  "args": [
    "-y", "mcp-remote",
    "https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/",
    "--silent",
    "--header", "X-SF-REALM:us1",
    "--header", "X-SF-TOKEN:your-observability-api-token"
  ]
}
```

Matching `.env` lines:

```bash
ENABLE_SPLUNK_O11Y=true
SPLUNK_O11Y_GATEWAY_URL=https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/
SPLUNK_O11Y_REALM=us1
SPLUNK_O11Y_API_TOKEN=your-observability-api-token
```

For **Splunk Cloud MCP** (logs/platform), copy `Authorization: Bearer ...` and `splunk_tenant` from that server’s Cursor entry into `SPLUNK_CLOUD_MCP_*` variables instead.

### Step 2 — Edit `.env`

From the project root:

```bash
cp .env.example .env
```

Uncomment and fill in the block for the integration you need. Full template is in [`.env.example`](.env.example).

**Observability Cloud (typical):**

```bash
ENABLE_SPLUNK_O11Y=true
SPLUNK_O11Y_GATEWAY_URL=https://<your-region>.api.scs.splunk.com/system/mcp-gateway/v1/
SPLUNK_O11Y_REALM=us1
SPLUNK_O11Y_API_TOKEN=<observability-api-access-token>
# SPLUNK_O11Y_TOOL_PREFIX=o11y_   # default; only expose o11y_* tools
```

**Splunk Cloud MCP (platform / logs):**

```bash
ENABLE_SPLUNK_CLOUD_MCP=true
SPLUNK_CLOUD_MCP_URL=https://<your-region>.api.scs.splunk.com/system/mcp-gateway/v1/
SPLUNK_CLOUD_MCP_BEARER_TOKEN=<jwt-from-splunk-cloud-mcp-app>
SPLUNK_CLOUD_MCP_TENANT=<your-tenant-name>
```

**Splunk Enterprise (on-prem):**

```bash
ENABLE_SPLUNK_MCP=true
SPLUNK_MCP_URL=https://<splunk-host>:8089/services/mcp
SPLUNK_MCP_BEARER_TOKEN=<bearer-token>
```

Where to get tokens:

- **Observability API token** — Observability Cloud UI → your profile / API access, or your org’s documented token workflow. Used as `X-SF-TOKEN`.
- **Splunk Cloud MCP Bearer** — From the Splunk Cloud MCP application setup (encrypted JWT), not the same as the o11y token.
- **Realm** — Your Observability realm (e.g. `us1`, `eu0`); must match the org you query.

### Step 3 — Test MCP connectivity (`mcp-doctor`)

This starts `mcp-remote`, connects to the gateway, and lists tools. It does **not** print secrets.

```bash
troubleshoot-agent mcp-doctor
```

**Success** (Observability enabled) looks like:

```text
splunk_o11y: OK (12 tools)
  - o11y_get_apm_environments
  - o11y_search_alerts_or_incidents
  - o11y_get_apm_services
  ...
MCP ready.
```

**Common failures:**

| Output | Fix |
|--------|-----|
| `No MCP integrations enabled` | Set `ENABLE_SPLUNK_O11Y=true` (or another `ENABLE_*`) in `.env` |
| `Configuration error: enable_splunk_o11y requires: ...` | Fill in every required variable for that integration |
| `splunk_o11y: FAIL` + 401 | Wrong realm/token; use o11y headers only, not Cloud MCP Bearer |
| Hangs / `npx` not found | Install Node.js; ensure `npx` works in the same shell |
| Works in Cursor, fails here | Compare URL and headers character-for-character with `mcp.json` |

You can enable multiple servers; `mcp-doctor` reports each one (`splunk_o11y`, `splunk_cloud_mcp`, `splunk_enterprise_mcp`).

### Test MCP with the agent

After `mcp-doctor` shows `OK`, run chats that should return **real data** (not just generic advice):

```bash
# List APM environments (good first test)
troubleshoot-agent chat "Provide me a list of environments available in APM"

# Active alerts for a service (use your exact APM service name)
troubleshoot-agent chat "List active alerts for service my-api"

# APM services in an environment (replace env name if you know it)
troubleshoot-agent chat "List APM services in environment production"
```

What good output looks like:

- Environment names, alert summaries, incident links, or metric/APM JSON summarized in plain language.
- A short pause on first request while `mcp-remote` starts and the model calls tools.

What to avoid:

- Only JSON like `{"name": "o11y_..."}` with no follow-up — reinstall with `pip install -e .` and retry.
- “Please provide environment” when you asked for data — usually means MCP is off or `mcp-doctor` failed; fix connectivity first.

Use a **tool-capable** model. Remote models via LiteLLM (`gpt-4.1-mini`, etc.) generally handle tool calling well. For Ollama, `qwen2.5-coder:7b` is the default.

### Environment variable reference

| Variable | Required when | Description |
|----------|----------------|-------------|
| `ENABLE_SPLUNK_O11Y` | o11y | `true` to enable Observability MCP tools |
| `SPLUNK_O11Y_GATEWAY_URL` | o11y | Splunk Cloud MCP gateway base URL |
| `SPLUNK_O11Y_REALM` | o11y | Observability realm (`X-SF-REALM`) |
| `SPLUNK_O11Y_API_TOKEN` | o11y | Observability access token (`X-SF-TOKEN`) |
| `SPLUNK_O11Y_TOOL_PREFIX` | No | Default `o11y_` — filter tool names exposed to the agent |
| `ENABLE_SPLUNK_CLOUD_MCP` | Cloud MCP | `true` for Splunk Cloud platform MCP |
| `SPLUNK_CLOUD_MCP_URL` | Cloud MCP | Gateway or server URL |
| `SPLUNK_CLOUD_MCP_BEARER_TOKEN` | Cloud MCP | Bearer JWT for Cloud MCP |
| `SPLUNK_CLOUD_MCP_TENANT` | Cloud MCP | Tenant name (`splunk_tenant` header) |
| `ENABLE_SPLUNK_MCP` | Enterprise | `true` for on-prem Splunk MCP |
| `SPLUNK_MCP_URL` | Enterprise | Enterprise MCP endpoint |
| `SPLUNK_MCP_BEARER_TOKEN` | Enterprise | Bearer token for Enterprise MCP |
| `MCP_NPX_COMMAND` | No | Default `npx` |

Splunk MCP wiring matches Cursor’s `mcp-remote` pattern — configure gateway URLs and tokens in `.env` the same way as in Cursor MCP settings.

### LLM environment variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | All | Optional: `ollama`, `openai`, or `azure_openai` (auto-detected if unset) |
| `OPENAI_API_KEY` | openai | API key for LiteLLM / OpenAI-compatible endpoint |
| `OPENAI_BASE_URL` | openai | Base URL (e.g. `https://lite-llm-proxy.splunko11y.com/v1`) |
| `OPENAI_MODEL_NAME` | openai | Model name routed by proxy (default: `gpt-4.1-mini`) |
| `OLLAMA_BASE_URL` | ollama | Ollama API URL (default: `http://127.0.0.1:11434`) |
| `OLLAMA_MODEL` | ollama | Ollama model tag (default: `qwen2.5-coder:7b`) |
| `AZURE_OPENAI_*` | azure_openai | Endpoint, key, deployment name, API version |
| `LLM_TEMPERATURE` | All | Sampling temperature (default: `0.2`) |

---

## Slack demo setup

Demo flow for presenters: **Splunk Observability fires an alert → Slack channel → one bot investigates → reply in thread** (not 200 replies in the channel). Workshop attendees can watch without installing Slack.

### Architecture

```text
o11y detector → Slack integration → #splunk-observability-alerts-1
                                           ↓
                              troubleshoot-agent slack-listen (Socket Mode)
                                           ↓
                              LangGraph agent + o11y MCP tools
                                           ↓
                              Thread reply under the alert message
```

### Step 1 — Finish Slack app configuration

You already created the app. Complete these in [api.slack.com/apps](https://api.slack.com/apps):

#### A. Bot token scopes

**OAuth & Permissions** → **Bot Token Scopes**:

| Scope | Purpose |
|-------|---------|
| `channels:history` | Read alert messages |
| `channels:read` | Resolve channel name → ID |
| `chat:write` | Post investigation in thread |
| `channels:join` | Join public channel if needed |

Click **Install to Workspace** (or reinstall after adding scopes). Copy **Bot User OAuth Token** → `SLACK_BOT_TOKEN` (`xoxb-...`).

#### B. Signing secret

**Basic Information** → **App Credentials** → **Signing Secret** → `SLACK_SIGNING_SECRET`.

#### C. Socket Mode (no public URL required)

1. **Socket Mode** → Enable.
2. Generate an **App-Level Token** with scope `connections:write`.
3. Copy token → `SLACK_APP_TOKEN` (`xapp-...`).

#### D. Event subscriptions

1. **Event Subscriptions** → Enable.
2. **Subscribe to bot events** → add `message.channels`.
3. Save changes.

### Step 2 — Create and wire the alerts channel

1. In Slack, create a public channel: `#splunk-observability-alerts-1`.
2. Invite your bot: `/invite @your-bot-name` in that channel.
3. Optional: copy **channel ID** (`C...` from channel details) → `SLACK_ALERTS_CHANNEL_ID`.

### Step 3 — Connect Splunk Observability to Slack

In **Splunk Observability Cloud**:

1. Go to **Integrations** (or **Notification Services**) → **Slack**.
2. Connect your Slack workspace and authorize the integration.
3. Create or edit a **detector** (or use an existing one).
4. Under **Alert settings** / **Notifications**, add **Slack** and select `#splunk-observability-alerts-1`.
5. Save the detector.

When the detector fires, Observability posts an alert message to that channel (usually as an integration/bot message — the listener handles that).

**Quick test without waiting for a detector:** post a manual message in the channel:

```text
APM - Sudden change in service latency - my-service:prod (value: 0.64%)
```

### Step 4 — Configure `.env`

```bash
ENABLE_SLACK=true
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...
SLACK_ALERTS_CHANNEL_NAME=splunk-observability-alerts-1

# Required for live investigation (same as CLI chat)
ENABLE_SPLUNK_O11Y=true
SPLUNK_O11Y_GATEWAY_URL=...
SPLUNK_O11Y_REALM=...
SPLUNK_O11Y_API_TOKEN=...

# LLM (OpenAI-compatible example)
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://lite-llm-proxy.splunko11y.com/v1
OPENAI_MODEL_NAME=gpt-4.1-mini
```

### Step 5 — Install and verify

```bash
pip install -e ".[dev]"
troubleshoot-agent doctor
troubleshoot-agent mcp-doctor
troubleshoot-agent slack-doctor
```

Expected from `slack-doctor`:

```text
Slack: OK (workspace=... bot=... channel=#splunk-observability-alerts-1 id=C...)
Ready for slack-listen.
```

### Step 6 — Run the demo listener

In a dedicated terminal (keeps running during the demo):

```bash
troubleshoot-agent slack-listen
```

1. Fire a detector or post a test alert in `#splunk-observability-alerts-1`.
2. The bot posts `:mag: Troubleshooting agent is investigating...` **in the thread**.
3. After o11y MCP + LLM run, it posts the investigation summary **in the same thread**.

Press `Ctrl+C` to stop.

### Demo tips

| Tip | Why |
|-----|-----|
| One machine runs `slack-listen` | Socket Mode allows only one active connection per app |
| Use thread replies | Keeps the channel readable for the audience |
| Pre-run `mcp-doctor` | Avoids live demo MCP failures |
| Manual alert text works | No need to fire a real detector for every rehearsal |

### Slack environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ENABLE_SLACK` | Yes | `true` to enable Slack commands |
| `SLACK_BOT_TOKEN` | Yes | Bot token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | Yes | App-level token for Socket Mode (`xapp-...`) |
| `SLACK_SIGNING_SECRET` | Yes | From app credentials |
| `SLACK_ALERTS_CHANNEL_NAME` | No | Default `splunk-observability-alerts-1` (no `#`) |
| `SLACK_ALERTS_CHANNEL_ID` | No | Set if channel name lookup fails |

---

## Usage reference

| Command | When to use |
|---------|-------------|
| `troubleshoot-agent doctor` | Check LLM connectivity (Ollama, OpenAI-compatible, or Azure) |
| `troubleshoot-agent mcp-doctor` | After editing Splunk vars in `.env` — confirms MCP tools load |
| `troubleshoot-agent chat "..."` | Ask questions; with MCP enabled, agent calls live Splunk/o11y tools |
| `troubleshoot-agent chat --trace "..."` | Same as `chat`, with brief agent/MCP trace logs in the terminal |
| `troubleshoot-agent slack-doctor` | Verify Slack bot + alerts channel (demo) |
| `troubleshoot-agent slack-listen` | Listen for alerts in Slack; investigate in thread (demo) |

**Suggested order on a new machine:** `doctor` → configure `.env` → `mcp-doctor` → `chat` with a concrete Observability question.

**Demo presenter order:** `doctor` → `mcp-doctor` → `slack-doctor` → `slack-listen` → fire alert → check [Observability](#observability) logs (and optional Splunk APM / Galileo traces).

---

## Observability

Three complementary layers: **terminal logs** (live demo), **Splunk OTel APM** (distributed traces), **Galileo** (LLM/agent traces).

### 1. Agent trace logs (default on)

Brief one-line logs during `slack-listen` and `chat --trace`:

```text
INFO [inv=slack:1730...] investigate service=Verification env=Brian-E-AD-Capital
INFO [inv=slack:1730...] agent start provider=openai mcp_tools=12
INFO [inv=slack:1730...] llm turn=1 tools=o11y_search_alerts_or_incidents
INFO [inv=slack:1730...] mcp o11y_search_alerts_or_incidents ERROR invalid parameter
INFO [inv=slack:1730...] done turns=2 tool_calls=2 duration_ms=8420
```

| Variable | Default | Purpose |
|----------|---------|---------|
| `AGENT_LOG_TRACE` | `true` | Enable brief agent/MCP logs |
| `AGENT_LOG_DEBUG` | `false` | Verbose tool args (workshop only) |
| `LOG_FORMAT` | `text` | `text` or `json` |

```bash
troubleshoot-agent chat --trace "List APM environments"
AGENT_LOG_TRACE=false troubleshoot-agent slack-listen   # quiet terminal
```

### 2. Splunk OTel (APM traces)

Hybrid **auto + manual** instrumentation:

- **Auto:** `httpx` (LLM HTTP calls), Python logging correlation
- **Manual spans:** `slack.alert`, `agent.investigation`, `agent.llm.turn`, `mcp.tool`

Install optional dependencies:

```bash
pip install "troubleshooting-agent[observability]"
opentelemetry-bootstrap -a install
```

**Mode A — programmatic** (set in `.env`):

```bash
ENABLE_SPLUNK_OTEL=true
OTEL_SERVICE_NAME=troubleshooting-agent
SPLUNK_ACCESS_TOKEN=<ingest-token>    # NOT the o11y MCP API token
SPLUNK_REALM=us1                      # defaults from SPLUNK_O11Y_REALM if set
```

Then run normally:

```bash
troubleshoot-agent slack-listen
```

**Mode B — wrapper** (no code init):

```bash
export OTEL_SERVICE_NAME=troubleshooting-agent
export SPLUNK_REALM=us1
export SPLUNK_ACCESS_TOKEN=<ingest-token>
opentelemetry-instrument troubleshoot-agent slack-listen
```

In Splunk APM, look for service **troubleshooting-agent** with root span `slack.alert` and children `agent.investigation`, `mcp.tool`, and httpx client spans.

### 3. Galileo (agent / LLM / tool traces)

Galileo captures prompts, tool calls, and responses via `GalileoAsyncCallback` on the LangGraph invoke.

```bash
pip install "troubleshooting-agent[observability]"

ENABLE_GALILEO=true
GALILEO_API_KEY=...
GALILEO_PROJECT=troubleshooting-agent
GALILEO_LOG_STREAM=slack-investigations
```

View traces in Galileo Cloud → your project → log stream. Each Slack alert gets `investigation_id=slack:<message_ts>` in metadata.

**Demo checklist:** terminal logs → Splunk APM trace → Galileo trace for the same alert.

---

## Development

With the virtualenv activated (or `uv run`):

```bash
ruff check src tests
ruff format src tests
mypy
pytest
```

```bash
AZURE_INTEGRATION=1 pytest -m azure_integration
```

```bash
OPENAI_INTEGRATION=1 pytest -m openai_integration
```

Optional integration tests (requires running Ollama and the pulled model):

```bash
OLLAMA_INTEGRATION=1 pytest -m integration
```

---

## Troubleshooting setup issues

| Problem | What to try |
|---------|-------------|
| Agent still uses Ollama after setting `OPENAI_*` | Reinstall (`pip install -e .`); ensure `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set; or set `LLM_PROVIDER=openai` explicitly |
| `OpenAI-compatible LLM unreachable` | Check `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL_NAME`; run `troubleshoot-agent doctor` |
| `llm_provider=openai requires` | Set `OPENAI_API_KEY` and `OPENAI_BASE_URL` when `LLM_PROVIDER=openai` |
| `Azure OpenAI unreachable` | Verify `AZURE_OPENAI_*` vars; deployment name must match Azure portal; check API version |
| `llm_provider=azure_openai requires` | Set all four `AZURE_OPENAI_*` variables when `LLM_PROVIDER=azure_openai` |
| `Ollama unreachable` | Start Ollama or set `LLM_PROVIDER=openai` / `azure_openai` for a remote LLM. |
| Configured model not in tag list | Run `ollama pull qwen2.5-coder:7b` or set `OLLAMA_MODEL` to a model from `ollama list`. |
| `troubleshoot-agent: command not found` | Activate `.venv` or reinstall with `pip install -e ".[dev]"`. |
| Slow first response | Normal while the model loads into memory; later requests are faster. |
| `splunk-mcp-server` errored in Cursor | Fix in Cursor MCP settings first; use the same URL/token in `.env` |
| `mcp-doctor` hangs or fails | Ensure `npx` is on PATH; test MCP in Cursor; check network/TLS for the gateway URL |
| HTTP 401 on o11y tools | Confirm `SPLUNK_O11Y_REALM` and `SPLUNK_O11Y_API_TOKEN` only — do not mix in Splunk Cloud MCP Bearer/tenant |
| HTTP 401 on Splunk Cloud MCP | Use `ENABLE_SPLUNK_CLOUD_MCP` with `SPLUNK_CLOUD_MCP_BEARER_TOKEN` and `SPLUNK_CLOUD_MCP_TENANT` |
| MCP enabled but agent ignores tools | Run `mcp-doctor` first; use `qwen2.5-coder:7b`; `pip install -e .` for latest agent fixes |
| Agent asks for env/service but does not list data | `mcp-doctor` must be OK; check token/realm; try example chats in [Test MCP](#test-mcp-with-the-agent) |
| Model prints JSON tool calls but no data | Reinstall editable package; agent parses JSON tool calls and wraps `params` for o11y tools |

---

## Roadmap

| Phase | Scope |
|-------|--------|
| **0** | Ollama + LangGraph agent, tool registry |
| **1** (current) | Splunk Observability MCP gateway, OpenAI/Azure LLM providers, `mcp-doctor` |
| **2** | Hardening: tool allowlists, session pooling, Splunk MCP fixes |
| **3** | Slack notifications → agent investigations |

Keep secrets in `.env` only (never commit). Gateway URLs and tokens should match your Cursor MCP settings where applicable.

Dependencies and optional dev packages: [`pyproject.toml`](pyproject.toml).
