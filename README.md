# Troubleshooting Agent

AI agent for troubleshooting applications and systems. Phase 0 connects to a local [Ollama](https://ollama.com) model via LangChain/LangGraph, with extension points for Splunk Observability, Splunk MCP, and Slack in later phases.

## What you need

| Requirement | Notes |
|-------------|--------|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) or Homebrew on macOS |
| Ollama | Local LLM runtime (install steps below) |
| Model | **Qwen 2.5 Coder** (`qwen2.5-coder:7b`) — good for tool use and troubleshooting |

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

### 4. Verify everything works

```bash
troubleshoot-agent doctor
```

Expected: `Ollama: OK`, your model in the list, then `Ready.`

If `doctor` warns that the configured model is missing, run `ollama pull qwen2.5-coder:7b` again or fix `OLLAMA_MODEL` in `.env`.

### 5. Run the agent

```bash
troubleshoot-agent chat "Why might service X return 503?"
```

With uv, without activating the venv:

```bash
uv run troubleshoot-agent chat "Why might service X return 503?"
```

---

## Usage reference

| Command | Description |
|---------|-------------|
| `troubleshoot-agent doctor` | Check Ollama URL, list models, validate configured model |
| `troubleshoot-agent chat "..."` | Send a troubleshooting question to the agent |

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

---

## Roadmap

| Phase | Scope |
|-------|--------|
| **0** (current) | Ollama + LangGraph agent, tool registry, builtin test tool |
| **1** | Splunk Observability tools (alerts, APM, metrics) |
| **2** | Splunk MCP (log search) |
| **3** | Slack notifications → agent investigations |

Cursor MCP servers configured in the IDE are separate from this Python app until Phase 1 adds an MCP or API bridge.

## Project layout

```
src/troubleshooting_agent/
  config.py          # Settings from environment
  llm/ollama.py      # ChatOllama factory + health check
  tools/             # Tool registry and future integrations
  agent/             # LangGraph agent loop
  cli.py             # Typer CLI
```

Dependencies and optional dev packages: [`pyproject.toml`](pyproject.toml).
