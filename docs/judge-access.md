# How judges can try RedPen

> Fill this in on Mon (Abdullah). Test it in an incognito window with a non-team account if possible.

1. **Open the app:** <Gemini Enterprise app URL>. Judges need to be added as users. Send their emails to <team leader> or ask the organisers to add them.
2. **Try the chat agent:** open **RedPen Insight** and ask:
   - "Which CLOs in my programme are at risk?"
   - "Why did the AI pass criterion 'Explanation of algorithms' in DSA201 A1?"
3. **Run an audit yourself:**
   - Option A (manual): open **RedPen Audit (Pro)** → input `/RedPen/Assessments/DSA201/A1/` → run.
   - Option B (automatic): upload a new folder under `/RedPen/Assessments/<MODULE>/<ASSESSMENT>/` with `rubric.txt` and `clo-map.txt` first and `brief.txt` last. The audit starts automatically.
4. **See the results:** verdict in `/RedPen/Verdicts/`, Jira board <Jira board URL>, revised briefs in `/RedPen/Revised/`.
5. **Video:** <link> · **Repo:** https://github.com/L0adn9/redPen
