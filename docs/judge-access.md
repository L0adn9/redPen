# How judges can try RedPen

## The app (prototype, updated for the final)
1. **Hosted app:** [https://redpen-apu.streamlit.app](https://redpen-apu.streamlit.app). The sidebar has four pages.
   - **Audit → Past audits:** 9 full audits open instantly, no code needed (4 real APU Level 2 briefs, 5 sample briefs). Each shows the verdict (HIGH / MEDIUM / LOW), the three AI students' grades, the learning outcomes no longer proven, and the evidence (every answer and mark). For HIGH or MEDIUM: **Fix** (redesign options) → **Approve**.
   - **Agents:** the seven Gemini agents, drawn as a live diagram. **Replay a saved audit** works for everyone. With the judge code, **Run live on Gemini** runs the agents on a real APU brief, or on **your own assignment** (upload the brief, plus the marking scheme and learning outcomes if they're separate: PDF, Word or text). Each agent's exact prompt is shown next to its output. After a live run, **Continue as the lecturer: fix and approve** opens that result on the Audit page.
   - **Register:** every audited assessment, the live Jira board, and the monthly re-audit schedule.
   - **How it works:** the pipeline, the three AI students, what the verdict means, and the calibration.
   - **Judge code** (`[given in the submission form]`, enter it in the sidebar): live runs, and Approve writes a **real card to our Jira Cloud board**. Type **your own email** before Approve to receive the report and revised brief via Gmail, plus a Google Calendar invitation for HIGH exposure.
2. **Run it yourself (5 minutes):**
   ```bash
   git clone https://github.com/L0adn9/redPen && cd redPen
   pip install -r requirements.txt
   echo "OPENROUTER_API_KEY=sk-or-..." > .env          # Gemini models via OpenRouter
   python3 tools/test_engine.py                         # 44 offline tests, no key needed
   python3 tools/redpen_audit.py --check                # key works?
   python3 tools/redpen_audit.py data/pilot-real/CCP/A1 # full audit of a real APU brief (~30 s)
   python3 tools/redpen_insight.py "Which CLOs in my programme are at risk?"
   streamlit run streamlit_app.py
   ```
3. **Evidence:** pilot runs in `data/pilot-real/runs/` (Flash and Pro), calibration in `docs/calibration/results.md`, all agent prompts in `agents/`.

## Gemini Enterprise (not built yet)
Our Gemini Enterprise licences had not been issued by the final on 17 Nov, so nothing below is running yet. The kit is ready: the paste sheet and build guide are in `agents/gemini-enterprise/`. Once a licence arrives, the plan is:

1. **Open the app:** `<Gemini Enterprise app URL>`. Judges must be added as users: send their emails to the team leader or ask the organisers.
2. **Chat agent:** open **RedPen Insight** and ask:
   - "Which CLOs in my programme are at risk?"
   - "Why did the AI pass the safety-aspects criterion in the Concurrent Programming assignment?"
3. **Run an audit:**
   - Manual: **RedPen Audit** → input `/RedPen/Assessments/CT074/A1/` → run.
   - Automatic: upload a new folder under `/RedPen/Assessments/<MODULE>/<ASSESSMENT>/` with `rubric.txt` and `clo-map.txt` first and `brief.txt` last. The audit starts by itself within about 10 minutes (Drive triggers are polled).
4. **Results:** verdicts in `/RedPen/Verdicts/`, Jira board `<Jira board URL>`, revised briefs in `/RedPen/Revised/`.

**Video:** `[link]` · **Repo:** https://github.com/L0adn9/redPen
