# Audit workflow: build guide (Abdullah)

Build in this order (for the top-5 build, 13–17 Nov). Test after each step and don't move on until it works.

**Start with [`agents/gemini-enterprise/README.md`](../gemini-enterprise/README.md)**: run `python3 tools/ge_pack.py` and paste from the generated `PASTE-SHEET.md` (never from older copies). Check every test run with `python3 tools/ge_compare.py`.

**Already proven in the prototype:** every instruction block below runs unchanged in `tools/redpen_audit.py` (29 s per audit on Flash, contract-clean). Before pasting into Gemini Enterprise, `python3 tools/test_engine.py` must pass. Compare each Gemini Enterprise verdict with the saved run in `data/demo-runs/<MODULE>_<ASSESSMENT>/06-verdict.json`. Exact button names in Gemini Enterprise may differ slightly from the text below; the steps follow Google's Workflow Builder docs.

## 0. App setup (Fri, ~30 min)
1. Google Cloud console → search **Gemini Enterprise** → **Apps** → **Create app**. Location: **global**. Name: `RedPen`.
2. App → **Configurations → Feature management**: turn ON **chat agents**, **Workflow Builder / workflows**, and **model selector**. Save.
3. App → **Connected data stores → New data store → Google Drive**. Include only the `/RedPen` folder ID (from the folder's URL). Allow search + upload/create file actions.
4. Share the app with Hassan, and share the Drive `/RedPen/` folder with him as **Editor**.
5. Create the Drive folders (see `TASKS.md` → Agreements #1) and upload the 5 sample assessments from `data/sample-assessments/` (one folder per assessment: `brief.txt`, `rubric.txt`, `clo-map.txt`).
6. Run your day-1 checks (#1, 2, 8, 9, 10 in `docs/day1-checklist.md`) and fill in the results.

## 1. Linear path, manual trigger (Fri)
1. Open the app URL → **Agents → New agent → Workflow** (or *Build manually*). Name: **RedPen Audit**.
2. **Trigger: Manual**, with one required input: `Assessment folder path` (e.g. `/RedPen/Assessments/DSA201/A1/`).
3. Add **Gemini Agent** steps in order, pasting each file's instructions:
   1. `01-intake.md`: Drive restricted to `/RedPen/Assessments/`
   2. `02-persona-copy-paster.md`
   3. `03-persona-prompt-engineer.md`
   4. `04-persona-honest-helper.md`
   - Personas 2–4 only need the Intake output. If the builder supports parallel branches, run them in parallel; otherwise run them in sequence.
4. Run it on `DSA201/A1`. Check that each persona output is valid JSON and has answers for every selected task.
5. **Before adding more steps, run day-1 check #13** (step scope). In the last persona step, ask it to repeat the module code from the Intake step.
   - If it can't see the Intake output, switch to [`fallback-pass-through.md`](fallback-pass-through.md) now, not on Saturday night.

## 2. Examiner + Verdict + save (Sat morning)
1. Add `05-examiner.md` (model **Flash**: calibration showed Flash 7 of 7 within one grade band, Pro 5 of 7; see `docs/calibration/results.md`) after the personas.
2. Add `06-verdict.md`.
3. Add the **Drive upload** action (step 5 in `06-verdict.md`), saving to `/RedPen/Verdicts/`. Approve the review prompt.
4. Run it on `DSA201/A1` and `DAN301/A2` (prototype results: HIGH and LOW). Paste each verdict into `python3 tools/check_verdict.py -` (Ctrl-D to finish) to check it matches the contract before Hassan's workflow reads it. Expect DSA201 to be HIGH or MEDIUM and DAN301 to be LOW. If DAN301 comes out HIGH, the Examiner is too generous: re-read rule 4.
5. When it works, message Hassan: **"Verdict files are landing in /Verdicts/"**.

## 3. Calibration round 1 (Sat afternoon)
Follow `docs/calibration/README.md`.

## 4. Triggers (Sat evening)
1. Duplicate the workflow (or add a second trigger). **Event trigger: Google Drive**, filter on new files in `/RedPen/Assessments/`.
   - The event gives you a file (e.g. `brief.txt`). The Intake instructions already say "use the folder that file is in".
   - **Upload `rubric.txt` and `clo-map.txt` first and `brief.txt` last**, so the folder is complete when the trigger fires. Write this rule in `docs/judge-access.md` too.
2. Turn the workflow **ON**. Event triggers only poll while it's on.
3. Test: upload a new assessment folder. The audit should start without you clicking anything.

## 5. Sync 2: integration test with Hassan (Sat ~9 PM)
Drop the hero assignment in and watch it go Audit → verdict → Fix → Jira. If the hand-off fails, use the fallback in `agents/verdict-format.md`.

## 6. Monthly schedule + Flash vs Pro (Sun)
1. **Schedule trigger:** monthly, 1st Monday, 09:00, time zone **Asia/Kuala_Lumpur**. Input: the hero assignment folder, or the top 3 due soonest if a loop works (day-1 check #10).
2. **Duplicate** the workflow as **RedPen Audit (Pro students)**. Set the 3 persona steps to **Pro**; keep `"model": "pro"` in the Verdict step. The Examiner stays **Flash** in both copies, so only the AI students change.
3. Run both on the hero assignment (CT074 CCP A1). Screenshot both verdicts side by side. For reference, the prototype's full-Pro run gave a different verdict on 2 of 4 real briefs (`data/pilot-real/runs/`).

## 7. Chat agent (Sun)
Build `07-insight-chat-agent.md` after Hassan says "Jira connected".

## 8. Export for the repo (Mon)
Screenshot every workflow canvas and agent settings page into `agents/audit/screenshots/`. If you changed any instructions in the UI, copy the final text back into these `.md` files.

## Antigravity (screenshot each use into `docs/antigravity/`)
- Prompt ideas: "Generate 5 more realistic university assessment briefs with rubrics and CLO maps in this format: <paste DSA201 files>", "Draw an architecture diagram (Mermaid) of this system: <paste README architecture section>", "Here's a JSON verdict and an error from my workflow; why is it failing?"
