---
name: redpen-agents-page
description: Add an "Agents" page to the RedPen web app that shows the agent orchestration diagram and, for a saved audit, each agent's exact prompt next to its real output. Use when asked to show the prompts or orchestration inside the app.
---

# Agents page in the RedPen app

The app is `../streamlit_app.py`. Its sidebar menu is `st.radio("Menu", ["Audit", "Register", "How it works"], ...)` and each page is a function (`page_audit`, `page_register`, `page_how`) dispatched by a dict at the bottom of the file. (If you cannot edit files outside this workspace, tell the user to allow non-workspace file access in Antigravity's settings or to open the `redPen` folder for this task.)

1. Add a menu item **"Agents"** and a function `page_agents()`; add it to the dispatch dict. Change nothing else on the other pages.
2. At the top: one caption, "Every step is a Gemini agent. These are the exact prompts and the exact outputs of a saved audit."
3. Draw the orchestration with `st.graphviz_chart` (a DOT string, no new dependency): Intake -> Copy-paster / Prompt engineer / Honest helper (same rank, parallel) -> Examiner -> Verdict -> Redesign -> Lecturer approval -> Jira / Gmail / Calendar.
4. A selectbox of saved audits from `../data/demo-runs/` (folders that contain `06-verdict.json`), default `CCP_A1`.
5. For each agent in order, an `st.expander` titled "<n>. <agent name>": two columns, left the prompt (load it the way `tools/redpen_audit.py` `instructions()` does: the ``` block under "## Instructions" in `agents/audit/<file>` or `agents/fix/01-redesign.md`), shown with `st.code(..., language=None)`; right the step's output from the chosen run (`01-intake.json`, `02-copy_paster.json`, `02-prompt_engineer.json`, `02-honest_helper.json`, `05-examiner.json`, `06-verdict.json`, `07-redesign.json` when present) with `st.json(..., expanded=False)`.
6. Use the existing helpers and style (`ui()`, `rp-*` CSS classes) where they fit.
7. Run `cd .. && .venv/bin/python tools/test_engine.py` and show the result. Do not start the app; ask the user to run `.venv/bin/streamlit run streamlit_app.py` and open the Agents page.
8. Append the task to `AG-LOG.md`.
