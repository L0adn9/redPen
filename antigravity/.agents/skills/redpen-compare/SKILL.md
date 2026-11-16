---
name: redpen-compare
description: Compare an orchestrator run with the RedPen app's saved run of the same assignment (exposure level, AI students' totals, CLOs at risk). Use to check that the agents reproduce the app's result.
---

# Compare with the RedPen app

1. Find the run folder (latest in `runs/` unless the user names one).
2. Run: `../.venv/bin/python orchestrator.py compare runs/<run-id>` (add a saved-run name such as `CCP_A1`, `DSTR_LW1`, `DSTR_LW2`, `WAPP_GA`, `BET150_A1` if it can't find one).
3. Present the table and the result line, and interpret it honestly:
   - **MATCH**: same exposure level.
   - **CLOSE**: one level apart. Our own repeated runs move by one level sometimes (CCP has come out HIGH and MEDIUM), so this is expected variation, not an error.
   - **DIFFERENT**: two levels apart. Look at which AI student's total moved most and quote the Examiner's justification for the biggest score differences from both runs' `05-examiner.json`.
4. Persona totals within about 10 points are normal for independent runs.
5. Append the task to `AG-LOG.md`.
