# Part 3 — Four-node graph + skills

**Prerequisite:** [shared/README.md](../shared/README.md)

Reference implementation — run from this directory:

```bash
cd part3_agent
troubleshooting-agent slack-listen
```

## Architecture

Part 3 runs a **four-node LangGraph workflow** (not the Part 1 single ReAct loop):

```
START → identify → categorize → investigate → report → END
```

| Node | What it does |
|------|----------------|
| `identify` | Code-first MCP alert search, then `identify_llm` / `identify_tools` sub-loop if needed |
| `categorize` | Deterministic Python: alert → APM / IM / RUM / Synthetics |
| `investigate` | Code-loads product skill, runs `investigate_llm` / `investigate_tools` ReAct |
| `report` | Code-loads `troubleshoot-report`, formats final output |

## Key files

| File | Purpose |
|------|---------|
| `agent.py` | `run_chat` → compiles and invokes Part 3 graph |
| `graph.py` | Four-node workflow + named ReAct subgraphs |
| `skill_tools.py` | `load_skill_content`, `list_skills`, LangChain tools |
| `skill_categorizer.py` | Alert → product type (no LLM) |
| `skill_router.py` | Base prompt + troubleshoot overview |
| `skills/` | Playbook library (source of truth) |
| `skills/search-logs/indexes.md` | Splunk index/sourcetype catalog for the workshop tenant |

## Log index catalog

The investigate node injects **`search-logs/indexes.md`** (YAML frontmatter + tables) so the agent searches the right index first — e.g. `splunk4rookies-workshop` instead of `main` on **o11y-workshop-amer**.

To refresh for a new tenant:

1. Connect Splunk Cloud MCP (`splunk_get_indexes`, `splunk_run_query`).
2. Copy [skills/search-logs/indexes.example.md](skills/search-logs/indexes.example.md) → `indexes.md`.
3. Fill in index volumes, sourcetypes, and example SPL from discovery queries.
4. Run `pytest tests/part3/test_skill_tools.py -k catalog`.


## Skills at runtime

| Step | Skill loaded |
|------|----------------|
| identify | `get-alerts-or-incidents` (preloaded into identify prompt) |
| categorize | rules from `troubleshoot/reference.md` (code) |
| investigate | `troubleshoot-{apm,im,rum,synthetics}-incidents` + **search-logs** (code-loaded by product) |
| report | `troubleshoot-report` (code-loaded) |

## Galileo / observability

Galileo traces show **named workflow nodes** instead of repeated `Agent:Agent`:

```
part3_investigation
├── identify
│   ├── identify_llm
│   └── identify_tools
├── categorize
├── investigate
│   ├── investigate_llm
│   └── investigate_tools
└── report
```

RunnableConfig metadata includes `agent.node`, `agent.product_type`, and `agent.skills_loaded`.

Terminal trace (`AGENT_LOG_TRACE=true`, default) shows numbered steps, graph node transitions, and a final **Agent response** block. See [shared/README.md](../shared/README.md#what-you-see-in-the-terminal).

Per-investigation JSONL trace files are written to `shared/logs/investigations/` by default
(`AGENT_LOG_DIR`, disable with empty value). Each Slack/CLI run gets one file with
node snapshots, alert IDs, MCP tool calls, and LLM turns — useful when the report
references a different `detectorId` than the Slack alert.

## Demo script

1. Same alert through Part 1 → Part 2 (manual prompt edit) → Part 3 (structured graph).
2. Show Galileo session named by Observability `eventId` and workshop part (e.g. `part3_agent`) with distinct node names.
3. Show thread reply from `slack-listen`.

## Facilitator checklist

- [ ] `doctor`, `mcp-doctor`, `slack-doctor` pass
- [ ] Demo detectors fire alerts in the Slack channel
- [ ] `AGENT_LOG_TRACE=true` for live narration
- [ ] Galileo project/stream configured
