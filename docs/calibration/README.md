# Calibration: can the AI Examiner mark like a lecturer? (Abdullah)

**Why:** judges will ask "isn't this just AI grading AI?" This is the answer, with numbers.

## What you need
3–5 real student answers that an APU lecturer has **already marked**, with the marks per criterion, plus the brief and rubric. Get them anonymised (no names or IDs) and with the lecturer's permission. Don't put them in the repo; keep them in Drive `/RedPen/Calibration/`.

## Steps
1. Create a copy of the Examiner step (or a small workflow): Intake on the brief → Examiner, where the "persona answer" is the real student answer.
2. Record each criterion's lecturer mark and Examiner mark in `data/calibration/calibration-template.csv` (marks only, no student text).
3. Compute, per sample: the total %, the grade for each, and whether they're **within one grade band**. Also compute the **mean absolute difference** in total %.
4. If more than 1 in 5 is off by more than one band: tighten the Examiner instructions (e.g. "when unsure between two bands, choose the lower"; "quote the evidence before deciding"), re-run as round 2, and keep both rounds.

## Report it like this (deck + README)
> "We calibrated RedPen's Examiner on N lecturer-marked assignments: N of N within one grade band, mean difference X marks (round 2; round 1 was Y)."

Message Hassan when done: **"Examiner calibrated: N of 5 within one grade"**.
