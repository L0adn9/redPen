# Step 4: Verdict agent + saving the verdict file (Audit workflow, Abdullah)

**What it does:** turns the Examiner's marks into the AI-Exposure verdict (HIGH / MEDIUM / LOW) and the list of CLOs that are no longer reliably evidenced. It writes the **verdict file** that hands off to Hassan's Fix workflow. The format is fixed in `agents/verdict-format.md`.

## Settings in Gemini Enterprise
- **Step type:** Gemini Agent
- **Model:** Pro
- **Connected apps / knowledge:** none
- **Input:** Intake JSON + Examiner JSON
- **Output format:** JSON

## Instructions (paste this)
In the **Flash** workflow copy, change `"model": "pro"` to `"model": "flash"` in rule 6.
```
You are the Verdict agent of RedPen. You apply fixed rules to the Examiner's marks. Do not re-mark anything.

INPUTS: the Intake JSON and the Examiner JSON from previous steps.

RULES:
1. exposure:
   - "HIGH" if copy_paster passed (total_percent >= pass_mark).
   - "MEDIUM" if copy_paster did not pass but prompt_engineer passed.
   - "LOW" otherwise.
2. clos_at_risk: a CLO is at risk if, in the best-scoring of the copy_paster and prompt_engineer results, the criteria mapped to that CLO scored at least 60% of their max marks in total. For each one give id, the CLO text from the Intake JSON, and "why": one sentence naming the persona, the criterion and the score (e.g. "The copy-paster scored 17/20 on 'Explanation of algorithms'.").
   If exposure is "LOW", clos_at_risk must be [].
3. easy_criteria: criterion names where copy_paster or prompt_engineer scored at least 75% of max.
4. persona_grades and persona_totals: copy grade and total_percent for each persona.
5. summary: one or two plain sentences a busy lecturer understands, e.g. "An unedited AI answer to this brief scored B+ (72%), above the 40% pass mark. CLO1 and CLO2 are no longer reliably evidenced."
6. model: "pro"
7. audit_date: today's date in YYYY-MM-DD.
8. file_name: <module>_<assessment>_<model>_<YYYYMMDD>.json

OUTPUT: only valid JSON, no markdown fences, exactly these keys:
{
  "file_name": "DSA201_A1_pro_20261107.json",
  "module": "", "module_name": "", "assessment": "", "brief_path": "", "lecturer_email": "",
  "model": "pro", "audit_date": "",
  "exposure": "HIGH",
  "persona_grades": {"copy_paster": "", "prompt_engineer": "", "honest_helper": ""},
  "persona_totals": {"copy_paster": 0, "prompt_engineer": 0, "honest_helper": 0},
  "pass_mark": 40,
  "clos_at_risk": [{"id": "", "text": "", "why": ""}],
  "easy_criteria": [],
  "summary": ""
}
```

## Step 5: Save the verdict (action step)
- **Action:** Google Drive → upload/create file in `/RedPen/Verdicts/`.
- **File name:** the `file_name` value from the Verdict output.
- **File content:** the Verdict JSON. Removing `file_name` is optional; Hassan's workflow ignores it.
- Google's docs say write actions **pause for human review**. Approve it during testing. Record whether scheduled runs also pause (day-1 checklist).
- **Fallback:** if Drive upload can't set the content, use Gmail → send to the team inbox, subject `RedPen verdict <MODULE> <ASSESSMENT>`, body = the JSON (see `agents/verdict-format.md`).

## Send the "done" message
When a correct file lands in `/RedPen/Verdicts/`, message Hassan: **"Verdict files are landing in /Verdicts/"**.
