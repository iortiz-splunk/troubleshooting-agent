# Part 3 — Full agent + troubleshoot skill

**Prerequisite:** [shared/README.md](../shared/README.md)

Reference implementation — run from this directory:

```bash
cd part3_agent
troubleshooting-agent slack-listen
```

## Key files

| File | Purpose |
|------|---------|
| `agent.py` | Full agent with builtins + MCP |
| `skill_router.py` | Loads the **troubleshoot** orchestration skill into the prompt |
| `skills/` | Playbook library (orchestration + product workflows) |

## Skills

At runtime, only **`troubleshoot`** is injected into the system prompt. It orchestrates:

1. **get-alerts-or-incidents** — load alert payload
2. Categorize **APM / IM / RUM / Synthetics**
3. **troubleshoot-{apm,im,rum,synthetics}-incidents** — product workflow
4. **troubleshoot-report** — structured final output

The agent follows links to other skills under `skills/` during the investigation.

Terminal trace (`AGENT_LOG_TRACE=true`) includes `skill=troubleshoot` in investigation metadata.

## Demo script

1. Same alert through Part 1 → Part 2 (manual prompt edit) → Part 3 (orchestrated workflow).
2. Show Galileo session named by Observability `eventId`.
3. Show thread reply from `slack-listen`.

## Facilitator checklist

- [ ] `doctor`, `mcp-doctor`, `slack-doctor` pass
- [ ] Demo detectors fire alerts in the Slack channel
- [ ] `AGENT_LOG_TRACE=true` for live narration
- [ ] Galileo project/stream configured
