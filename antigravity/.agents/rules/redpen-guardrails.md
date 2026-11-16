---
trigger: always_on
description: Safety and honesty rules for every task in the RedPen workspace.
---

# RedPen guardrails

1. **Never print, log or commit an API key, token or password.** Keys live in `../.env` (gitignored). Refer to them by name only (`GEMINI_API_KEY`).
2. **Nothing leaves the machine without the user's explicit OK.** Do not send email, create Jira issues or calendar events, push to git or deploy. `orchestrator.py approve` only prepares files in `outbox/`; run it only after the user names the option to approve.
3. **Human in the loop.** When a run reaches the approval gate, show the redesign options and ask the user which one to approve. Never choose for them.
4. **Do not edit the agent prompts in `../agents/` unless the user asks.** The same prompts are pasted into Gemini Enterprise; changing them silently breaks that match.
5. **Do not start long-running servers** (for example `streamlit run`). Ask the user to run them in their own terminal.
6. **Use `../.venv/bin/python`** for every Python command.
7. **After any code change, run the tests** (`../.venv/bin/python test_orchestrator.py`, and `cd .. && .venv/bin/python tools/test_engine.py` if you touched `../tools/` or `../streamlit_app.py`) and show the result.
8. **Never invent numbers or results.** Only report what a run, a file or a test actually shows. If something failed, say so plainly.
9. **Log every task.** At the end of each task, append one entry to `AG-LOG.md` in this folder: date and time, the user's request in one line, the skill used (if any), files created or changed, commands run, and the outcome (including failures).
