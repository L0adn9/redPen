# Saved audit runs (demo mode)

Full runs of the Audit engine on our 5 **sample** assessments (`data/sample-assessments/`, written by us, not real APU briefs).
Every step's output is saved, so the app can replay them instantly with `load_demo("<folder>")`. Run on Gemini Flash, 8 Nov 2026.

| Assessment | Module | Exposure | Copy-paster | Prompt engineer | Honest helper | CLOs at risk |
|---|---|---|---|---|---|---|
| BET150 A1 | Business Ethics | **HIGH** | A+ (82%) | A+ (94%) | A+ (80%) | CLO1, CLO2 |
| DAN301 A2 | Data Analytics in Practice (Level 3) | **LOW** | F (15%) | F (18%) | F (0%) | - |
| DBS202 A1 | Database Systems | **HIGH** | A+ (89%) | A+ (93%) | F (0%) | CLO1, CLO2, CLO3 |
| DSA201 A1 | Data Structures & Algorithms | **HIGH** | A+ (89%) | A+ (95%) | A+ (89%) | CLO1, CLO2, CLO3 |
| SEP310 A2 | Software Engineering Project Management | **LOW** | F (0%) | F (0%) | F (0%) | - |

HIGH = the copy-paster passed. MEDIUM = only the prompt engineer passed. LOW = neither passed.
The two LOW ones need evidence an AI can't invent (values from the student's own supervised notebook; the team's real commit history, signed meeting minutes and peer-feedback forms), which is exactly the kind of redesign RedPen proposes.

Refresh with: `python3 tools/redpen_audit.py data/sample-assessments/*/* --save-demo` (6 API calls per assessment).
