# Where we stopped (Thu 12 Nov 2026, 18:35 MYT)

**Deadline:** prototype submission **Fri 13 Nov, 12:00 PM MYT** (aim to submit by 10 AM). Top 5 pitch 17 Nov must use Gemini Enterprise.

## Done
- Audit engine `tools/redpen_audit.py`: `run_audit()`, `load_demo()`, Gemini-only guard, OpenRouter or AI Studio key (`.env`, gitignored), `set_credentials()`, `--check`.
- Demo runs: `data/demo-runs/` (5 synthetic sample audits).
- Calibration: all 7 real assignments marked by hand first (`sample_assingments_unmarked/calibration/reference-marks.md`).
  - Round 5 (Gemini 3 Flash, current Examiner prompt): **7 of 7 within one grade band, 5 same grade, mean gap 4.4 points**. `data/calibration/results-round5.csv`.
  - Round 6 (Pro, `google/gemini-4-argon`) was cut off after 2 samples (73 vs 78, 71 vs 86). Rerun: `REDPEN_MODELS=google/gemini-4-argon python3 tools/calibrate.py sample_assingments_unmarked/calibration --round 6` (delete `_examiner-round6/` first).
  - Rounds 1-4 history: `docs/calibration/results.md` (needs round 5 added).
- Architecture diagram `docs/architecture.png`, video script `docs/demo-script.md`, key docs `docs/api-keys.md`.

## Start here next
1. **Pilot on real APU briefs** (the deck's key local stat, IDEA.md §7). Make folders `data/pilot-real/<MOD>/<A>/` with `brief.txt`, `rubric.txt`, `clo-map.txt` from `sample_assingments_unmarked/Assignments 2 year 2 sem/possible rubrics/`:
   - CCP A1 (Airport, Report + System schemes), DSTR LW1 (hospital, video + documentation criteria, pages 7-8), DSTR LW2 (parcel; Part B Q&A is live), WAPP GA (documentation + implementation).
   - Add a `--label` option to the CLI, then run each on Flash (`google/gemini-3-flash-preview`) and Pro (`google/gemini-4-argon`) for the Flash vs Pro slide. Copy the Flash runs into `data/demo-runs/`.
   - Headline: "X of 4 real APU briefs passable by AI with zero effort".
2. **Streamlit app** (Hassan has pushed nothing since 10 Nov; build it if he hasn't): demo mode default (`load_demo`), live run behind a password, redesign (`agents/fix/01-redesign.md`), Approve button, Jira card (REST, secrets), email (SMTP), `.ics` invite, revised brief download. Deploy on Streamlit Cloud.
3. Update `docs/demo-script.md` and `docs/calibration/results.md` with the round 5 + pilot numbers; deck PDF (≤10 MB) and README (problem, solution, research, teamwork, impact, time spent, architecture).
4. Before making the repo public: scrub teammates' names/TP numbers (MAE report: Kaung Htet TP077453, Muntasir Uzzaman Mashrafi TP088872; DSTR code: Pwint Yati Oo TP101449, Htet Htet Naing TP098108, Thu Thu San). Ask the user first.
5. Antigravity screenshots (required), record the video, Hassan submits.

Rules: no Claude co-author trailers on commits; only Gemini models; never commit `.env`.
