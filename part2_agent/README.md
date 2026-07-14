# Part 2 — Skills (lite auto-inject)

**Prerequisite:** [shared/README.md](../shared/README.md)

Part 2 uses the **same ReAct loop as Part 1**, but injects **one playbook** from `skills/` per investigation based on keywords in the alert or user message.

## How skill injection works

```text
Slack or CLI message → keyword router → one SKILL.md → Part 1 ReAct loop
```

| Skill | Workshop role | Loaded when |
|-------|---------------|-------------|
| `alert-triage` | Fallback first step | `alert`, `incident`, `triggered`, `detector` — or no domain match |
| `latency-spike` | **Facilitator demo** | `latency`, `duration`, `p99`, `slow` |
| `error-rate` | **Participant lab** (starter stub) | `error`, `errors`, `5xx` (complete during lab) |
| `investigation-report` | **Always injected** | Reporting format for every final reply — no raw JSON dumps |

Implementation: [`skill_inject.py`](skill_inject.py) — Part 2 does **not** import Part 3.

With `AGENT_LOG_TRACE=true` (default), the terminal shows a structured trace including `Skill loaded: latency-spike` and the final **Agent response** block. See [shared/README.md](../shared/README.md#what-you-see-in-the-terminal).

## Run

```bash
cd part2_agent
troubleshooting-agent chat "Investigate latency on Verification"
troubleshooting-agent chat "Investigate elevated 5xx on Verification"
troubleshooting-agent slack-listen
```

## Facilitator script (~25–35 min)

1. **Recap Part 1** (3 min) — same Verification latency alert; note inconsistent tool order.
2. **Skill anatomy** (5 min) — open `skills/latency-spike/SKILL.md`: frontmatter, tool sequence, do-not rules.
3. **Live demo** (8 min) — run Part 2 on a latency alert; trace shows `skill loaded=latency-spike`; expect `o11y_search_alerts_or_incidents` then `o11y_get_apm_service_latency`.
4. **Contrast gaps** (3 min) — no exemplar traces, no report template, may pick wrong alert without Part 3 anchoring.
5. **Participant lab** (15–20 min) — complete `skills/error-rate/SKILL.md` (see below).
6. **Teaser Part 3** (2 min) — same alert through the four-node graph in `part3_agent/`.

### Optional teaching moment

Briefly show **manual** wiring: paste a playbook section into `prompt.py`, run once, then revert and rely on auto-inject so participants see both authoring and runtime selection.

## Participant lab: error-rate skill

**Goal:** Complete the starter stub so the injector picks `error-rate` and the agent pulls error metrics.

**Answer key (facilitators only):** [`skills/error-rate/SKILL.md.answer`](skills/error-rate/SKILL.md.answer)

**Steps:**

1. Open `skills/latency-spike/SKILL.md` as a reference for structure.
2. Edit `skills/error-rate/SKILL.md` — complete frontmatter `description`, `alert_signals`, and `mcp_tools`.
3. Write the tool sequence: search alerts → `o11y_get_apm_service_errors_and_requests`.
4. Add 2–3 interpretation bullets (error count vs request volume).
5. Add at least one **Do not** rule.
6. Run: `troubleshooting-agent chat "Investigate elevated 5xx on Verification"` with `AGENT_LOG_TRACE=true`.
7. Confirm trace shows `skill loaded=error-rate` and at least two MCP tool calls.

**Success criteria:**

- Injector logs `skill=error-rate`
- Agent cites metric JSON in the reply, not generic advice

**Stretch alternatives** (same template in `skills/_template/SKILL.md`):

| Skill idea | Complexity |
|------------|------------|
| `request-spike` (traffic surge) | Low–medium — uses `o11y_get_apm_services` |
| `alert-triage-only` | Lowest — good for short sessions |

## Intentional gaps vs Part 3

| Capability | Part 2 | Part 3 |
|------------|--------|--------|
| Agent shape | Single ReAct | 4-node graph (identify → categorize → investigate → report) |
| Skills loaded | **One** domain skill + `investigation-report` | Product skill + `troubleshoot-report` per step |
| Alert anchoring | Part 1 search behavior | Strict `detectorId` / incident matching |
| Exemplar traces | No | Yes (`o11y_get_apm_exemplar_traces`) |
| Report format | `investigation-report` (short sections, no raw JSON) | Full `troubleshoot-report` sections |
| Galileo trace | `Agent:Agent` | Named nodes (`identify`, `investigate`, …) |

After Part 2, participants should be able to say: *a skill is a playbook with signals, tools, and guardrails — one skill helped, but I still wanted traces, reports, and the right alert ID.* Part 3 closes those gaps.

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Builds prompt with injected skill; logs skill name |
| `skill_inject.py` | Keyword routing + prompt assembly |
| `prompt.py` | Base system prompt |
| `skills/` | Playbook library (workshop edits here) |
| `skills/_template/SKILL.md` | Blank template for new playbooks |
