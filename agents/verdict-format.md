# Verdict file format (the hand-off between the two workflows)

**Owners:** Abdullah (writes it) and Hassan (reads it). **Change only after talking to each other.**

The **Audit** workflow (Abdullah) ends by saving one verdict file per audit run into Drive:

```
/RedPen/Verdicts/<MODULE>_<ASSESSMENT>_<MODEL>_<YYYYMMDD>.json
e.g. /RedPen/Verdicts/DSA201_A1_pro_20261107.json
```

The **Fix** workflow (Hassan) starts when a new file appears in `/RedPen/Verdicts/` and reads it.

## Fields

| Field | Type | Allowed values / example | Used by Fix workflow for |
|---|---|---|---|
| `module` | string | `"DSA201"` | Jira summary, labels, email subject |
| `module_name` | string | `"Data Structures & Algorithms"` | Email and Jira text |
| `assessment` | string | `"A1"` | Jira summary |
| `brief_path` | string | `"/RedPen/Assessments/DSA201/A1/brief.txt"` | Redesign agent reads the original brief |
| `lecturer_email` | string | `"lecturer@example.edu"` | Who approves + gets the email |
| `model` | string | `"flash"` or `"pro"` | Jira label `model-flash` / `model-pro` |
| `audit_date` | string | `"2026-11-07"` | Jira + email |
| `exposure` | string | `"HIGH"`, `"MEDIUM"` or `"LOW"` | **Condition step** (redesign only if HIGH or MEDIUM) |
| `persona_grades` | object | `{"copy_paster": "B+", "prompt_engineer": "A-", "honest_helper": "C"}` | Email + Jira description |
| `persona_totals` | object | `{"copy_paster": 68, "prompt_engineer": 77, "honest_helper": 48}` (percent) | Email + stats |
| `pass_mark` | number | `40` | Context |
| `clos_at_risk` | array | `[{"id": "CLO2", "text": "Analyse ...", "why": "..."}]` | Redesign agent + Jira labels `clo-2` |
| `easy_criteria` | array | `["Explanation of algorithms", "Complexity table"]` | Redesign agent targets these |
| `summary` | string | One or two plain sentences for the lecturer | Email first line |

## Rules
1. **Plain JSON only.** No markdown fences, no comments, no text before or after the JSON.
2. `exposure` is always uppercase.
3. `clos_at_risk` can be an empty list `[]` (for LOW).
4. Grades use the scale in the rubric (A+, A, B+, B, C+, C, D, F). Totals are percentages (0–100).

## Fallback hand-off (if the Drive trigger doesn't fire)
Abdullah's workflow emails the same JSON as the email body to the team inbox, with the subject `RedPen verdict <MODULE> <ASSESSMENT>`. Hassan's workflow uses a **Gmail event trigger** on that subject instead of the Drive trigger. Gmail and Drive are both listed as event-trigger sources.

If neither trigger works: Abdullah adds Hassan's Redesign agent and actions as extra steps at the end of the Audit workflow (one workflow).

## Examples
See `data/fake-verdicts/`: one HIGH and one LOW. Hassan builds the Fix workflow against these before Abdullah's real verdicts exist.
