---
name: redpen-ge-builder
description: Step-by-step help building RedPen's workflows and chat agent in Gemini Enterprise from the paste sheet. Use when the user is building or debugging the Gemini Enterprise version.
---

# Build RedPen in Gemini Enterprise

Sources (read, don't change): `../agents/gemini-enterprise/PASTE-SHEET.md`, `../agents/gemini-enterprise/README.md`, `../agents/audit/00-build-guide.md`, `../agents/fix/00-build-guide.md`, `../agents/verdict-format.md`.

1. Ask what the user is building (Audit workflow, Fix workflow, Insight chat agent, a connector) and what they see on screen (they can paste a screenshot).
2. Give the **next single step**: which button, which field, and the exact text from the paste sheet for that field (instructions, output schema, inputs).
3. Workflow 1 **RedPen Audit**: 6 agent steps in order (Intake, Copy-paster, Prompt engineer, Honest helper, Examiner, Verdict), then Drive "create file" in `/RedPen/Verdicts/`. If a step can only see the previous step's output, switch to the pass-through rules in `../agents/audit/fallback-pass-through.md`.
4. Workflow 2 **RedPen Fix**: condition (HIGH or MEDIUM) -> Redesign -> Approval step -> Jira create/update, Gmail send, Calendar event (HIGH only).
5. Chat agent **RedPen Insight**: instructions from `../agents/audit/07-insight-chat-agent.md`, data stores Jira + Drive.
6. After a test run, have the user paste the verdict JSON into a file and check it: `cd .. && .venv/bin/python tools/ge_compare.py <MODULE> <ASSESSMENT>`.
7. Append the task to `AG-LOG.md`.
