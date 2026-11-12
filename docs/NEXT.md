# Where we are (Thu 12 Nov 2026, 20:25 MYT)

**Deadline:** prototype submission **Fri 13 Nov, 12:00 PM MYT** (aim for 10 AM). Top-5 pitch on 17 Nov must use Gemini Enterprise.

## Done
- **App:** `streamlit_app.py` (+ `tools/redpen_fix.py`). Saved audits (9: 4 real APU briefs + 5 samples, each with redesigns) → verdict → redesign options → lecturer Approve → Jira card / email / .ics invite / revised brief. Live audit of uploaded PDF/DOCX/TXT. Key swap + model test in the sidebar. Tested headless: no errors.
  - Run: `.venv/bin/streamlit run streamlit_app.py` (venv already set up; or `pip install -r requirements.txt`).
- **Pilot (real APU briefs, Flash):** CCP HIGH (copy-paste A 77%), DSTR LW1 HIGH (C 50%), DSTR LW2 MEDIUM, WAPP LOW. 2 of 4 passed by copy-paste; 4 CLOs across 2 modules at risk. Pro: 2 of 4 verdicts differ (stricter). `data/pilot-real/`.
- **Calibration:** Flash 7/7 within one grade band, mean gap 4.4; Pro 5/7, 5.9. Examiner switched to Flash. `docs/calibration/results.md`.
- **Docs:** README filled with real numbers, `docs/demo-script.md` updated, deck at `deck/deck.html` → `deck/RedPen-deck.pdf` (12 slides, 0.7 MB).

## Still to do (in order)
1. **Deploy to Streamlit Community Cloud** (user must log in with GitHub; repo must be public or app given access). Main file `streamlit_app.py`. Secrets: `OPENROUTER_API_KEY`, `APP_PASSWORD`, optional `JIRA_BASE_URL`/`JIRA_EMAIL`/`JIRA_API_TOKEN` (API token from id.atlassian.com, user creates it), `SMTP_*`, `DEMO_LECTURER_EMAIL`. Put the link in README "Try it".
2. **Antigravity:** the user must actually use it (e.g. open the repo, ask it to explain/refactor something, generate a sample brief) and screenshot each use into `docs/antigravity/`, fill the table, then fill slide 10 in `deck/deck.html` and re-render:
   `cd deck && chromium --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf=RedPen-deck.pdf "file://$PWD/deck.html"`
3. **Video** (3 min) from `docs/demo-script.md`; upload, link in README.
4. **Scrub teammates' names/TP numbers** before going public (ask the user first): MAE report (Kaung Htet TP077453, Muntasir Uzzaman Mashrafi TP088872), DSTR code headers (Pwint Yati Oo TP101449, Htet Htet Naing TP098108, Thu Thu San). They live in `sample_assingments_unmarked/` and git history.
5. README: "Time spent", video + app links. Make repo public. Hassan (leader) submits: title, Theme 2, summary, repo URL, deck PDF, demo link.

Rules: no Claude co-author trailers; only Gemini models; never commit `.env`.
