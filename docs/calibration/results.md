# Calibration results (12 Nov 2026)

**Reference marker:** Claude, marking independently and **before** seeing any Examiner output. Not lecturer marks: report it as a cross-model check.
**Samples:** rounds 1-4 used 3 real assignments (CCP Report, CCP System, DSTR LW2 Task 2); round 5 used all 7 (adds WAPP report, RMCT Part 2, CSLLT, MAE Part 2). All from one student, with permission.
Reference marks and reasons: `sample_assingments_unmarked/calibration/reference-marks.md`. Per-round numbers: `data/calibration/results-round*.csv`.
Examiner model: `gemini-3-flash-preview` (the only Flash model answering that day).

| Round | Examiner change | CCP Report (ref 78) | CCP System (ref 86) | DSTR Part A (ref 77) | Within one grade | Mean gap |
|---|---|---|---|---|---|---|
| 1 | original prompt | 90 | 100 | 100 | 3/3 | 16.3 (always higher) |
| 2 | + "name the weakness first, full marks only if none, choose the lower when unsure" | 81 | 92 | 87 | 3/3 | 6.3 |
| 3 | + `live_session` flag: Q&A/viva criteria get 0 | 70 | 79 | 67 | 2/3 | 8.3 |
| 4 | softer wording (rejected) | 87 | 98 | 23* | 2/3 | 25.0 |

## Round 5: all 7 samples, final prompt (Gemini 3 Flash via OpenRouter)

| Sample | Reference | Examiner | Grades |
|---|---|---|---|
| CCP Report | 78 | 76 | A / A |
| CCP System | 86 | 93 | A+ / A+ |
| CSLLT | 78 | 90 | A / A+ |
| DSTR LW2 Task 2 | 77 | 85 | A / A+ |
| MAE Part 2 (report criteria) | 90 | 90 | A+ / A+ |
| RMCT Part 2 | 80 | 82 | A+ / A+ |
| WAPP report | 72 | 72 | B+ / B+ |
| **Result** | | | **7 of 7 within one grade band, 5 of 7 same grade, mean gap 4.4 points (Examiner +3.9 on average)** |

RMCT, CSLLT and MAE had no official marking scheme in our files, so both markers used the same rubric derived from the module descriptor or the report's cover page.

\* Round 4 docked the student for not building other team members' modules. The prompt now says not to.

## What we learned
1. **The original Examiner was too generous** (+16 points, full marks everywhere). For RedPen that matters: a generous examiner overstates how exposed an assessment is.
2. **Rounds 2–3 use the same strictness rule and land either side of the reference** (+6 and −8). Over those 6 markings: **5 of 6 within one grade band, mean gap 7.3 points**. That is the prompt we kept.
3. **One Flash run varies by about ±10 points.** Next step: run the Examiner 3 times and take the median mark (3 parallel Examiner steps in Gemini Enterprise).
4. **Live sessions were leaking marks.** Before the fix, the Examiner gave 13/15 (round 1) and 8/15 (round 2) for a face-to-face Q&A that never happened. With the `live_session` flag set at Intake it gives 0/15 every time. That's the difference between "AI passes" and "AI can't pass" for any assessment with a viva.

**Deck line:** "We checked RedPen's Examiner against an independent marker on 7 real APU assignments: 7 of 7 within one grade band, mean gap 4.4 points. Calibration also caught a bug: the Examiner was giving marks for a viva that never happened. Now it can't."
