# Troubleshooting Agent

AI agent for troubleshooting applications and systems. It uses a local [Ollama](https://ollama.com) model via LangChain/LangGraph and can connect to **Splunk Observability** and **Splunk Enterprise MCP** servers (same transport as Cursor: `mcp-remote` over stdio).

**Quick start with Splunk:** [New machine setup](#new-machine-setup) → [Splunk MCP setup](#splunk-mcp-setup) → `mcp-doctor` → [Test MCP with the agent](#test-mcp-with-the-agent).

## Contents

- [What you need](#what-you-need)
- [New machine setup](#new-machine-setup) (Ollama + Python)
- [Splunk MCP setup](#splunk-mcp-setup) (configure, test, example chats)
- [Usage reference](#usage-reference)
- [Development](#development)
- [Troubleshooting setup issues](#troubleshooting-setup-issues)

## What you need

| Requirement | Notes |
|-------------|--------|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) or Homebrew on macOS |
| Ollama | Local LLM runtime (install steps below) |
| Model | **Qwen 2.5 Coder** (`qwen2.5-coder:7b`) — good for tool use and troubleshooting |
| Node.js `npx` | Required when Splunk MCP integrations are enabled (runs `mcp-remote`) |

Dependencies are declared in [`pyproject.toml`](pyproject.toml). There is no separate `requirements.txt`; install the project in editable mode and pip (or uv) resolves everything from that file.

---

## New machine setup

Follow these steps in order on a fresh clone or new computer.

### 1. Install Ollama

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

### 4. Verify Ollama

```bash
troubleshoot-agent doctor
```

Expected:

```text
Ollama: OK
Available models:
  - qwen2.5-coder:7b
Ready.
```

If the configured model is missing, run `ollama pull qwen2.5-coder:7b` or fix `OLLAMA_MODEL` in `.env`.

### 5. Run the agent (Ollama only)

Without MCP, the agent answers from the local model only (no live Splunk/Observability data):

```bash
troubleshoot-agent chat "Why might service X return 503?"
```

With uv, without activating the venv:

```bash
uv run troubleshoot-agent chat "Why might service X return 503?"
```

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

Use a **tool-capable** model (`qwen2.5-coder:7b` is the default). Keep Ollama running during `chat` (same as for `doctor`).

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

### How it works (short)

```text
troubleshoot-agent chat
    → LangGraph agent (Ollama + tools)
    → McpSessionManager keeps mcp-remote alive
    → npx mcp-remote <gateway-url> --header X-SF-REALM:... --header X-SF-TOKEN:...
    → o11y_* tools (alerts, APM, metrics, traces)
```

This matches Cursor’s MCP wiring so you only configure credentials once.

---

## Usage reference

| Command | When to use |
|---------|-------------|
| `troubleshoot-agent doctor` | Before anything else — Ollama up and model pulled |
| `troubleshoot-agent mcp-doctor` | After editing Splunk vars in `.env` — confirms MCP tools load |
| `troubleshoot-agent chat "..."` | Ask questions; with MCP enabled, agent calls live Splunk/o11y tools |

**Suggested order on a new machine:** `doctor` → configure `.env` → `mcp-doctor` → `chat` with a concrete Observability question.

---

## Development

With the virtualenv activated (or `uv run`):

```bash
ruff check src tests
ruff format src tests
mypy
pytest
```

Optional integration tests (requires running Ollama and the pulled model):

```bash
OLLAMA_INTEGRATION=1 pytest -m integration
```

---

## Troubleshooting setup issues

| Problem | What to try |
|---------|-------------|
| `Ollama unreachable` | Start Ollama (`ollama serve` on macOS, or the Windows tray app). Check `OLLAMA_BASE_URL` in `.env`. |
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
| **1** (current) | Splunk Observability MCP gateway + Splunk Enterprise MCP bridge, `mcp-doctor` |
| **2** | Hardening: tool allowlists, session pooling, Splunk MCP fixes |
| **3** | Slack notifications → agent investigations |

Keep MCP gateway URLs and tokens in `.env` only (same values as Cursor MCP settings; never commit secrets).

## Project layout

```
src/troubleshooting_agent/
  config.py          # Settings from environment
  llm/ollama.py      # ChatOllama factory + health check
  mcp/               # MCP bridge (gateway params, session manager)
  tools/             # Tool registry and Splunk/Slack stubs
  agent/             # LangGraph agent loop
  cli.py             # Typer CLI (doctor, mcp-doctor, chat)
```

Dependencies and optional dev packages: [`pyproject.toml`](pyproject.toml).
