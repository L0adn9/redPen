---
name: redpen-explain
description: Write ORCHESTRATION.md, a judge-ready explanation of RedPen's agent orchestration and prompt design, using only facts from the repo. Use when asked to explain or document how the agents work.
---

# Explain the orchestration

Read `orchestrator.py`, every prompt file under `../agents/audit/` and `../agents/fix/`, the schemas in `../agents/schemas/`, `../agents/verdict-format.md` and `../agents/gemini-enterprise/README.md`. Do not change any of them.

Write `ORCHESTRATION.md` in this folder with:
1. **A Mermaid diagram** of the whole flow: lecturer's files -> Intake -> three AI students (parallel) -> Examiner -> Verdict -> exposure-rule guardrail -> HIGH or MEDIUM? -> Redesign -> lecturer approval -> Jira / Gmail / Calendar / revised brief. Add the monthly scheduled re-audit and the RedPen Insight chat agent reading the Jira register.
2. **One row per agent**: name, its job, what it receives, what it returns, prompt file, schema file.
3. **Orchestration patterns used**, each with the line of `orchestrator.py` that implements it: dependency graph executed in waves, parallel fan-out, schema validation, self-correction retry with the validation errors, deterministic guardrail on the exposure rule, conditional step, human approval gate, full trace per run.
4. **Prompt design**: for each agent quote 1-3 exact lines from its prompt that make it behave correctly (for example the Examiner scoring live viva criteria 0, the Copy-paster submitting unedited, the Verdict rule). Quote exactly.
5. **Gemini Enterprise mapping**: which workflow step each agent becomes (from `../agents/gemini-enterprise/README.md`).

Keep it under 220 lines. Then append the task to `AG-LOG.md`.
