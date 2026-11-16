---
name: redpen-audit
description: Run RedPen's multi-agent audit (Intake, three AI students in parallel, Examiner, Verdict, Redesign) on an assignment folder and explain the result. Use when the user asks to audit, red-team or test an assignment.
---

# RedPen audit

## Steps
1. **Pick the assignment.** If the user named one, use it. Otherwise list the options and ask:
   - real APU briefs: `../data/pilot-real/CCP/A1` (module CT074-3-2), `../data/pilot-real/DSTR/LW1`, `../data/pilot-real/DSTR/LW2`, `../data/pilot-real/WAPP/GA` (module CT050-3-2-WAPP)
   - sample briefs: `../data/sample-assessments/<MODULE>/<ASSESSMENT>`
   - or a new folder the user gives, containing `brief.txt` (required), `rubric.txt` and `clo-map.txt` (optional).
2. **Check the key.** If `GEMINI_API_KEY` is not set in `../.env`, tell the user (they get a free key at aistudio.google.com and add `GEMINI_API_KEY=...` to `../.env` themselves; never ask them to paste it in chat). Offer `--replay <saved run>` as an offline fallback, and say clearly that a replay makes no Gemini calls.
3. **Show the plan first.** Run `../.venv/bin/python orchestrator.py agents` and show the user the agent list before running.
4. **Run the audit:**
   `../.venv/bin/python orchestrator.py audit <folder> --module <MODULE> --assessment <ASSESSMENT>`
   It takes about 1 minute on Gemini Flash. Stream the wave-by-wave output to the user.
5. **Open `runs/<run-id>/report.md`** and present: the exposure level, each AI student's grade and total vs the pass mark, the CLOs at risk and why, the agent table (waves, model, seconds, attempts, schema check) and any guardrail correction.
6. **If there is a redesign**, list the options (title, AIAS level, lane, recommended) and **ask the user which one to approve**. Then hand over to the `redpen-approve` skill. Do not approve yourself.
7. Append the task to `AG-LOG.md`.

## If something fails
- An agent fails its schema twice: report which agent and the errors from `trace.json`; do not hand-edit its output.
- Every model fails (quota): tell the user and offer `--replay`.
