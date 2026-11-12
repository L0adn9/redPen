# How judges can try RedPen

## Prototype (submitted 13 Nov)
1. **Hosted app:** `[link: Streamlit Community Cloud]`. Open **Saved audits**: 9 full audits replay instantly with no key (4 real APU Level 2 briefs, 5 sample briefs).
   - Pick **CT074-3-2 A1 · Concurrent Programming**: three AI students attempt it, the Examiner marks them, verdict **HIGH**, CLO2 and CLO3 at risk.
   - Scroll to **Fix**: redesign options (AIAS level, lane, extra marking time) → **Approve**.
   - The **outbox** below shows everything RedPen sends: the report email exactly as the lecturer gets it (download `.eml`), the review meeting (**Add to Google Calendar** or `.ics`), the revised brief and the verdict file.
   - **Judge password** (`[given in the submission form]`, enter it in the sidebar): Approve then writes a **real card to our Jira Cloud board** and reads it back live (key, status *Approved*, labels). The table at the bottom lists the board live from Jira. The password also unlocks live audits of your own brief.
   - **Get the real email:** with the password on, type **your own email** in the *Lecturer email* box before Approve. RedPen sends you the report and revised brief via Gmail, and for HIGH exposure a calendar invitation that lands in your Google Calendar.
   - **Monthly re-audit:** scroll to the bottom of Saved audits. RedPen re-audits the register on a schedule (GitHub Actions, 1st of every month 09:00 MYT) and comments each result on the Jira card.
2. **Run it yourself (5 minutes):**
   ```bash
   git clone https://github.com/L0adn9/redPen && cd redPen
   pip install -r requirements.txt
   echo "OPENROUTER_API_KEY=sk-or-..." > .env          # Gemini models via OpenRouter
   python3 tools/test_engine.py                         # 43 offline tests, no key needed
   python3 tools/redpen_audit.py --check                # key works?
   python3 tools/redpen_audit.py data/pilot-real/CCP/A1 # full audit of a real APU brief (~30 s)
   python3 tools/redpen_insight.py "Which CLOs in my programme are at risk?"
   streamlit run streamlit_app.py
   ```
3. **Evidence:** pilot runs in `data/pilot-real/runs/` (Flash and Pro), calibration in `docs/calibration/results.md`, all agent prompts in `agents/`.

## Final build on Gemini Enterprise (top 5, 17 Nov)
1. **Open the app:** `<Gemini Enterprise app URL>`. Judges must be added as users: send their emails to the team leader or ask the organisers.
2. **Chat agent:** open **RedPen Insight** and ask:
   - "Which CLOs in my programme are at risk?"
   - "Why did the AI pass the safety-aspects criterion in the Concurrent Programming assignment?"
3. **Run an audit:**
   - Manual: **RedPen Audit** → input `/RedPen/Assessments/CT074/A1/` → run.
   - Automatic: upload a new folder under `/RedPen/Assessments/<MODULE>/<ASSESSMENT>/` with `rubric.txt` and `clo-map.txt` first and `brief.txt` last. The audit starts by itself within about 10 minutes (Drive triggers are polled).
4. **Results:** verdicts in `/RedPen/Verdicts/`, Jira board `<Jira board URL>`, revised briefs in `/RedPen/Revised/`.

**Video:** `[link]` · **Repo:** https://github.com/L0adn9/redPen
