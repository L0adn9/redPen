# RedPen × Google Antigravity

This folder is RedPen's **Antigravity workspace** and its agent-orchestration engine. Three ways to watch RedPen's agents orchestrate:

1. **In the RedPen app** (hosted, for judges): the **Agents** page draws the agent graph and lights it up live as each Gemini agent starts and finishes, then shows every agent's exact prompt next to its exact output (`agents_page.py`).
2. **In Antigravity, as a swarm**: `/redpen-swarm` turns every RedPen agent into its own Antigravity worker; they hand work to each other on the live Swarm board.
3. **In the terminal**: `orchestrator.py audit` prints the waves as they run.

**Who built what:** Claude Code (Anthropic) set up this workspace: `orchestrator.py`, its tests, `AGENTS.md`, the guardrail rule and the skills. Google Antigravity's agent then ran the skills: the audits, comparisons, documentation, the app's Agents page and the browser test. `AG-LOG.md` is Antigravity's own record of every task, written by its agent as it worked. The agents themselves are Gemini models running the prompts in `../agents/`.

## Open it
1. Antigravity → **Open Folder** → `redPen/antigravity`.
2. Antigravity loads `AGENTS.md` (project context), `.agents/rules/redpen-guardrails.md` (always on) and the skills in `.agents/skills/`. Type `/` in the agent panel to see them.
3. For live Gemini runs, add a free key from aistudio.google.com to `redPen/.env` as `GEMINI_API_KEY=...`. Never paste it into the chat.
4. Dependencies are already in `../.venv`; on a fresh machine run `../.venv/bin/pip install -r requirements.txt`.
5. Agent panel settings: model **Gemini 3 Pro** (or the newest Gemini listed), mode **Planning**.

## Run sheet (what to type, in order)

| # | Type in Antigravity | What happens | Screenshot |
|---|---|---|---|
| 0 | `/redpen-swarm` audit CT074 | **The live showcase.** The coordinator adds 8 workers (intake, three AI students, examiner, verdict, verifier, redesign); they pass work by @mention, the verifier checks the verdict, then the coordinator asks you to approve. Uses Antigravity's own Gemini: no API key needed. Quota heavy: rehearse once, record it as a backup | the Swarm board (feed + @mention graph), the roster, the final report |
| 1 | `/redpen-audit` Audit the real CT074 Concurrent Programming brief | Shows the agent list, then runs Intake → 3 AI students in parallel → Examiner → Verdict → Redesign with live Gemini, and presents the report | the plan/task list, the wave-by-wave terminal output, the report |
| 2 | `/redpen-approve` Approve R1 | The human gate: prepares the Jira card, email, invite and revised brief in `outbox/` without sending | the outbox summary, the updated diagram |
| 3 | `/redpen-compare` | Compares with the RedPen app's saved run of CT074 | the comparison table |
| 4 | `/redpen-audit` Audit the WAPP brief | A LOW result: Redesign is skipped by the condition | the "skipped: Redesign" line |
| 5 | `/redpen-explain` | Antigravity writes `ORCHESTRATION.md` (diagram, agent table, patterns, quoted prompt lines) | the rendered file |
| 6 | `/redpen-agents-page` | Antigravity adds an **Agents** page to the web app (prompt next to output for every agent). Then run `.venv/bin/streamlit run streamlit_app.py` yourself and open it | the diff, the test result, the new page |
| 7 | `/redpen-browser-test` | Antigravity's browser agent tests the hosted app and writes `browser-test.md` | the browser recording, the report |
| 8 | `/redpen-ge-builder` (only if stuck in Gemini Enterprise) | Next-step help from the paste sheet | — |

For every task, screenshot Antigravity's **implementation plan**, **task list** and **walkthrough**. Those show its own agent orchestration. Save them in `../docs/antigravity/` as `2026-11-16_<name>_task<N>-<what>.png`. If a task fails, screenshot that too and leave the failure in `AG-LOG.md`.

## Without Antigravity (terminal)
```bash
cd redPen/antigravity
../.venv/bin/python orchestrator.py agents
../.venv/bin/python orchestrator.py audit ../data/pilot-real/CCP/A1 --module CT074-3-2 --assessment A1
../.venv/bin/python orchestrator.py approve runs/<run-id> R1
../.venv/bin/python orchestrator.py compare runs/<run-id>
../.venv/bin/python test_orchestrator.py          # 8 offline tests
```
Add `--replay CCP_A1` to an audit to replay a saved run with no API calls. Replays are labelled `replay` everywhere and are not committed.

## Orchestration patterns (for judges)

| Pattern | Where |
|---|---|
| Agent dependency graph executed in waves | `AGENTS` table and `Orchestrator.ready()` / `run()` |
| Parallel fan-out (three AI students at once) | `ThreadPoolExecutor` in `Orchestrator.run()` |
| Typed hand-offs: every output validated against a JSON schema | `schema_errors()`, `../agents/schemas/` |
| Self-correction: a rejected output goes back to the same agent with its errors | `Orchestrator.run_agent()` |
| Deterministic guardrail: the exposure rule is enforced in code, not trusted to the model | `Orchestrator.guard_verdict()` |
| Conditional step: Redesign only for HIGH or MEDIUM | `"when"` on the Redesign agent |
| Human approval gate: nothing is prepared until a person picks an option, and nothing is sent from here | `approve` command, `redpen-approve` skill |
| Model fallback: the next Gemini model is tried if one fails | `GeminiBackend.call()` |
| Full trace per run: prompt file and hash, model, seconds, attempts, schema result | `runs/<run-id>/trace.json`, `report.md` |
| Antigravity guardrails: no keys in output, no sending, no prompt edits, log every task | `.agents/rules/redpen-guardrails.md` |
| Swarm mode: each agent is an Antigravity worker; hand-offs go through `swarm-init` / `input` / `submit` / `finish`, so swarm runs get the same schema checks, guardrail and report | `redpen-swarm` skill, swarm section of `orchestrator.py` |
| Live view: the graph is redrawn on every agent event | `Orchestrator(on_event=...)`, `agents_page.py` |
