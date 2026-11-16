---
name: redpen-swarm
description: Run a RedPen audit as a live Antigravity swarm. Each RedPen agent (Intake, three AI students, Examiner, Verdict, Verifier, Redesign) is its own swarm worker, and they hand work to each other on the board. Use when the user wants to watch the agents orchestrate live, for example "/redpen-swarm audit CT074".
---

# RedPen audit as a swarm (you are the coordinator)

Load the **`swarm`** skill and follow it. You are the coordinator: you set up the run, add the workers, watch the board, and bring the lecturer decision to the user. **You do not do any agent's work yourself.**

Every command below runs from this workspace folder with `../.venv/bin/python orchestrator.py` (call it `ORCH`).

## 1. Set up
1. Pick the assignment (ask if unclear). Real APU briefs:
   - `../data/pilot-real/CCP/A1` with `--module CT074-3-2 --assessment A1` (Concurrent Programming, the demo assignment)
   - `../data/pilot-real/DSTR/LW1`, `../data/pilot-real/DSTR/LW2`, `../data/pilot-real/WAPP/GA` (`--module CT050-3-2-WAPP --assessment GA`)
   - or a folder the user gives with `brief.txt` (+ optional `rubric.txt`, `clo-map.txt`).
2. Run `ORCH swarm-init <folder> --module <M> --assessment <A>`. It prints `RUN=runs/<run-id>`. Use that path in every brief below.
3. Title the swarm: `swarm{action:"title", title:"RedPen audit <M> <A>"}`.

## 2. Add the workers (all in one turn)
Add these 8 workers with `swarm{action:"add"}`, leaving `model` off. Each brief is the **common procedure** below with `<AGENT>` and `<HANDOFF>` filled in.

| name | `<AGENT>` | `<HANDOFF>` when ACCEPTED |
|---|---|---|
| `intake` | `intake` | Post your one-line summary and `@copy-paster @prompt-engineer @honest-helper go`. **Start immediately.** |
| `copy-paster` | `copy-paster` | If the submit output says `NEXT: Examiner`, post your summary and `@examiner go`; otherwise post your summary with no @mention. |
| `prompt-engineer` | `prompt-engineer` | Same rule as copy-paster. |
| `honest-helper` | `honest-helper` | Same rule as copy-paster. |
| `examiner` | `examiner` | Post the three totals and `@verdict go`. |
| `verdict` | `verdict` | Post exposure, CLOs at risk and the guardrail line, then `@verifier check`. |
| `redesign` | `redesign` | Post the option titles (with AIAS level, lane) and `@coordinator ready for lecturer approval`. |

**Common procedure (put this in each brief, filled in):**
> You are the RedPen **<AGENT>** agent in a live audit. Run folder: `<RUN>`. Work from the workspace folder; use `../.venv/bin/python orchestrator.py` for every command.
> Unless you are `intake`, do nothing until a board post @mentions you with "go".
> 1. Get your instructions: `../.venv/bin/python orchestrator.py prompt <RUN> <AGENT>`. These are your instructions; follow them exactly, as that agent.
> 2. Get your input: `../.venv/bin/python orchestrator.py input <RUN> <AGENT>`. If it says you must wait, wait for your @mention.
> 3. Produce your output yourself, from the instructions and the input only. Do not read `../data/demo-runs/`, other runs in `runs/`, or any other agent's draft. Do not call other AI tools or the web.
> 4. Write only the JSON object to `<RUN>/drafts/<AGENT>.json`.
> 5. Submit: `../.venv/bin/python orchestrator.py submit <RUN> <AGENT> <RUN>/drafts/<AGENT>.json`. If it prints REJECTED, fix exactly the listed problems and submit again (at most 3 times; then post the errors and `@coordinator`).
> 6. When it prints ACCEPTED: <HANDOFF>. Keep board posts to one or two lines. Never paste your whole JSON on the board.

The 8th worker is a **verifier** (it checks, it does not author):
> You are the RedPen **verifier**. Run folder: `<RUN>`. Do nothing until @mentioned with "check". Then read `<RUN>/05-examiner.json`, `<RUN>/06-verdict.json` and `<RUN>/trace.json` and check: (a) each AI student's total in the verdict matches the Examiner's scores; (b) the exposure follows the rule (HIGH if copy_paster total >= pass_mark, else MEDIUM if prompt_engineer total >= pass_mark, else LOW); (c) every CLO at risk is one the Intake listed; (d) no criterion that needs a live session (viva, demo, presentation) got marks. If something is wrong, post it to whoever must fix it (`@examiner` or `@verdict`) and stop. If everything is right: if the exposure is HIGH or MEDIUM post `verified ✓ @redesign go`, else post `verified ✓ LOW: no redesign needed @coordinator`.

Then follow the `swarm` skill for the narrator and monitor (only if those skills are listed), and end your turn with the board link so the user can watch.

## 3. Watch
Use `swarm_wait` / `read_board`. Check progress any time with `ORCH status <RUN>`. If a worker stalls, nudge it by name with the board post that should have woken it. If a worker's output is rejected 3 times, tell the user plainly.

## 4. Lecturer approval (human in the loop)
When `@coordinator ready for lecturer approval` (or `LOW: no redesign needed`) arrives:
1. Run `ORCH finish <RUN>` and show the user the key parts of `<RUN>/report.md`: exposure, the three AI students' grades vs pass mark, CLOs at risk, the agent table, the guardrail line, the redesign options.
2. Ask the user which option to approve (or none). **Never choose for them.**
3. When they choose: `ORCH approve <RUN> <OPTION>`, then show what was prepared in `<RUN>/outbox/` and say that nothing was sent.
4. Optional: `ORCH compare <RUN>` to compare with the RedPen app's saved run.
5. Post `[done] <one-line summary>` with no @mention, then kill the workers (not the narrator or monitor) unless the user wants to keep them.
6. Append the run to `AG-LOG.md` (run id, assignment, verdict, approved option, any rejections or stalls).
