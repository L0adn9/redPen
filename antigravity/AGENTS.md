# RedPen: context for the Antigravity agent

RedPen is an AI red team for university assessments (APU Cloud Innovation Hackathon 2026, team Hassan + Abdullah).
Before an assignment is released, RedPen sends three AI students at it, marks them on the real rubric and tells the
lecturer which course learning outcomes (CLOs) the assignment can no longer prove. Then it proposes a redesign, and
after the lecturer approves it updates Jira, emails the report and books a review meeting.

## This workspace
This folder (`redPen/antigravity/`) is where we run and extend RedPen's agents with you. The rest of the repo is the
parent folder `..`:

| Path | What it is |
|---|---|
| `orchestrator.py` | The multi-agent orchestrator: runs the Gemini agents in waves, checks every output against its schema, self-corrects, enforces the exposure rule, stops at the lecturer approval gate. |
| `runs/<run-id>/` | One folder per run: each agent's JSON output, `trace.json`, `report.md` (diagram + results). |
| `test_orchestrator.py` | Offline tests (no API key). |
| `agents_page.py` | The app's **Agents** page: live agent graph + every agent's prompt and output. |
| `.agents/skills/redpen-swarm/` | Run the audit as an Antigravity swarm (one worker per RedPen agent). |
| `../agents/` | The agent prompts (the same text goes into Gemini Enterprise workflows) and `../agents/schemas/`. |
| `../streamlit_app.py`, `../tools/` | The RedPen web app (hosted at https://redpen-apu.streamlit.app) and its engine. |
| `../data/pilot-real/` | 4 real APU assignment briefs (CCP/A1, DSTR/LW1, DSTR/LW2, WAPP/GA). |
| `../data/sample-assessments/` | 5 synthetic sample briefs. |
| `../data/demo-runs/` | Saved RedPen app runs, used for comparison and offline replay. |

## The agents (in order)
1. **Intake** reads brief, rubric, CLO map.
2. **Copy-paster**, **Prompt engineer**, **Honest helper**: three AI students attempt the assignment, in parallel.
3. **Examiner** marks the three attempts on the real rubric.
4. **Verdict**: HIGH if the copy-paster passed, MEDIUM if only the prompt engineer passed, else LOW; lists CLOs at risk.
5. **Redesign** (only HIGH/MEDIUM): 2-3 redesigns that still test the same CLOs.
6. **Lecturer approval** (a human), then Jira card, Gmail report, Calendar invite, revised brief.

## How to run things
- Python: always `../.venv/bin/python` (it has every dependency).
- List agents: `../.venv/bin/python orchestrator.py agents`
- Audit: `../.venv/bin/python orchestrator.py audit ../data/pilot-real/CCP/A1 --module CT074-3-2 --assessment A1`
- Offline (no key): add `--replay CCP_A1`
- Tests: `../.venv/bin/python test_orchestrator.py` and `cd .. && .venv/bin/python tools/test_engine.py`

## Facts you may state (never invent numbers)
- Pilot: 2 of 4 real APU briefs passed by an unedited copy-paste; 4 CLOs across 2 modules no longer reliably evidenced.
- Calibration: the Examiner was within one grade band of independent reference marks on 7 of 7 real assignments
  (5 of 7 the same grade, mean gap 4.4 points). The reference marks came from an independent AI marker, not lecturers.
- A single audit can move one exposure level between runs; every verdict records its model and date.
