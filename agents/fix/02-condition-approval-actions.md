# Condition, approval and actions (Fix workflow, Hassan)

## Condition step (right after the trigger)
- **Variable:** `exposure` from the verdict file
- **Rule:** `exposure` **equals** `HIGH` **OR** `exposure` **equals** `MEDIUM` → go to the Redesign agent.
- **Else (LOW):** skip the redesign and go straight to "Jira create/update" with label `exposure-low`, status **Audited**, plus a short Gmail "No action needed" note. Still log it: the register should show LOW results too.

If the Condition step can't read a field from the JSON file directly (day-1 check #16), add a tiny **Gemini Agent** step first, "Read verdict":
- **Connected apps:** Google Drive, restricted to `/RedPen/Verdicts/`
- **Output format:** JSON
- **Instruction:** `Open the verdict JSON file that triggered this workflow (or the file path given as input) in /RedPen/Verdicts/ and output its content unchanged as JSON. No markdown fences, no extra text.`
Then point the Condition at its `exposure` field.

Also apply Abdullah's step-scope finding (day-1 check #13): if a step can only see the step just before it, every step in the Fix workflow must copy the verdict forward. Add this line to the end of the Redesign, Compose and action-prep agent instructions: `Also output the input verdict unchanged under the key "verdict".`

## Approval step (after the Redesign agent)
- **Approver:** the `lecturer_email` from the verdict. For the demo, use one of your own accounts as "the lecturer".
- **Message shown to the approver (paste and map the fields):**
```
RedPen audit: {module} {assessment} ({module_name})
AI-Exposure: {exposure}. Copy-paster scored {persona_grades.copy_paster}, prompt engineer {persona_grades.prompt_engineer}.
CLOs no longer reliably evidenced: {clos_at_risk ids}
Recommended redesign: {recommended}: {title of recommended option}
{email_summary}

Approve to: create the Jira redesign ticket, save the revised brief to Drive, email you the full report{and book a 30-min review if HIGH}.
Request changes to send feedback to the Redesign agent.
```
- If **Request info** is supported, add a yes/no + paragraph field: "Which option do you choose (R1/R2/R3) and any changes?"
- **If the approval step doesn't work** (day-1 check #3): stand-in = Gmail sends the summary, and the lecturer replies "APPROVE R1". A Gmail event trigger on replies continues the flow. For the demo, a manual continue is fine; say so honestly.

## Actions (after approval; each needs Google's built-in review, so approve them)

### 1. Jira: create or update the register issue
- **Search first:** Jira search with JQL `project = RP AND summary ~ "{module} {assessment}"`. If found → **update**; else → **create**. (Google's docs: write actions need search enabled to find IDs. Create needs the project ID + issue type ID.)
- **Summary:** `{module} {assessment}`
- **Issue type:** Task
- **Labels:** `exposure-{high|medium|low}`, `clo-1`, `clo-2` (one per CLO at risk, lowercase, no spaces), `model-{flash|pro}`, `module-{module lowercase}`
- **Status:** `Redesign proposed` before approval / `Approved` after approval. Create the issue as Audited, then move it.
- **Description:**
```
AI-Exposure: {exposure} (audit {audit_date}, persona model: {model})
Persona grades: copy-paster {..} / prompt engineer {..} / honest helper {..}
CLOs at risk: {id: text}
Easy criteria: {easy_criteria}
Recommended redesign: {recommended} {title} (AIAS level {n}, {lane} lane, +{minutes} min marking/student)
Verdict file: /RedPen/Verdicts/{file}
Revised brief: /RedPen/Revised/{module}_{assessment}_revised.txt
```

### 2. Drive: upload the revised brief
- **Folder:** `/RedPen/Revised/`
- **File name:** `{module}_{assessment}_revised.txt`
- **Content:** the original brief with the approved option's `revised_task_text` replacing the old task(s). Add a "Gemini Agent" step "Compose revised brief" before this if needed, with the instruction: `Rewrite the original brief replacing the selected tasks with revised_task_text of the approved option. Keep everything else identical. Add a line at the top: 'Revised by RedPen on <date>, approved by <lecturer>. AIAS level <n>.' Output plain text.`

### 3. Gmail: the verdict report to the lecturer
- **To:** `lecturer_email` · **Subject:** `RedPen: {module} {assessment} is {exposure} AI-exposure ({clos_at_risk ids} at risk)`
- **Body:**
```
Hi,

{email_summary}

What the AI did
- Copy-paster (pasted the brief into AI, no edits): {grade} ({total}%)
- Prompt engineer (strategic AI use): {grade} ({total}%)
- Honest student using AI as allowed: {grade} ({total}%)
Pass mark: {pass_mark}%

CLOs no longer reliably evidenced
- {id}: {text} ({why})

Approved redesign: {title}: AIAS level {n}, {lane} lane, about +{minutes} min marking per student.
Revised brief: /RedPen/Revised/{file}
Jira: RP issue "{module} {assessment}"

RedPen is a risk signal from simulated AI attempts marked by an AI examiner calibrated against lecturer marks. It does not assess any real student.
```

### 4. Calendar: review meeting (HIGH only)
- Add a second **Condition**: `exposure` equals `HIGH`.
- **Create event:** 30 min, next working day 10:00 (Asia/Kuala_Lumpur), title `RedPen review: {module} {assessment}`, guests: lecturer + the T&L centre address (for the demo, your second account). Description: the Jira summary + revised brief path.

## Done messages
- "Jira connected" (once the data store is live). Abdullah needs it for the chat agent.
- "Fix workflow works on fake verdicts" (when one HIGH run creates the Jira issue, revised brief, email and invite).
