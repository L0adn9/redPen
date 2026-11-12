# Demo video script (about 3 min) · prototype submission, Fri 13 Nov 12 PM

**Screen:** Abdullah drives the Streamlit app. **Voice:** split between both of you (H = Hassan, A = Abdullah).
Record each scene as a separate clip, so one failure doesn't ruin the take. Hero assignment: **CT074 Concurrent Programming, Asia Pacific Airport** (a real APU brief, Saved audits → first item).
Numbers in **bold** come from our saved runs (`data/demo-runs/`, `data/pilot-real/`) and `docs/calibration/results.md`. Never say a number you don't have.

| Time | Screen | Voice-over |
|---|---|---|
| 0:00 | Title card: RedPen. "They catch students. We fix assignments." | **H:** "Every university is buying AI detectors to catch students. They're unreliable, and they're too late. We think the problem is the assignment." |
| 0:12 | Run a new audit: upload the CCP brief PDF + rubric (or show it, then switch to Saved audits) | **A:** "A lecturer gives RedPen three things they already have: the brief, the rubric and the learning-outcome map. This is a real APU Level 2 assignment from this semester." |
| 0:25 | Run view: Intake, then the 3 AI students working (speed up 4x, label "sped up") | **A:** "Three AI students attempt it: one pastes the brief straight into a chatbot, one uses AI strategically, and one uses AI only the way the brief allows." |
| 0:50 | Examiner marks + Verdict card (CCP A1) | **H:** "An AI examiner marks them on the real rubric, like a lecturer without a detector. Pasting the brief straight into Gemini got an **A, 77%**, with zero effort. Verdict: **HIGH** exposure. This assignment no longer proves **CLO2 and CLO3**." |
| 1:10 | Switch to WAPP GA (LOW) | **A:** "Compare this one: half its marks come from a live demonstration to the lecturer. The AI students can't pass it. Same AI, different design. That's what we fix." |
| 1:25 | Back to CCP A1: redesign options | **H:** "RedPen proposes redesigns that still test the same learning outcomes: here a decision log plus a 5-minute in-class viva, about 8 extra minutes of marking per student. It targets exactly the criteria the AI passed easily." |
| 1:45 | Click **Approve** → Jira card on the RP board, email arrives, calendar invite, revised brief downloads | **H:** "Nothing changes until the lecturer approves. One click, and RedPen logs it in the Jira exposure register, emails the report, books a review meeting and hands back the revised brief." |
| 2:05 | Assessment Exposure Register table | **A:** "We ran it on **4 real APU briefs** from this semester. **2 of 4 were passed by a straight copy-paste**, a third by a student using AI strategically. **4 learning outcomes across 2 modules** are no longer reliably proven." |
| 2:20 | Calibration slide | **A:** "Isn't this AI marking AI? We marked 7 real assignments independently first, then let our examiner mark them: **7 of 7 within one grade band, average gap 4.4 points**. It even caught a bug: the examiner was giving marks for a viva that never happened." |
| 2:35 | Architecture slide (`docs/architecture.png`) | **H:** "The agents are plain instructions in our repo. The prototype runs them on Gemini; for the final we paste the same steps into Gemini Enterprise workflows, triggered from Drive, with an approval step and Jira, Gmail and Calendar actions. Built in Antigravity." |
| 2:50 | Slide: 3 and 6 months | **A:** "In 3 months, one programme's whole assessment bank is audited before the semester. In 6, every programme, re-audited every month, because every model release makes old assignments weaker." |
| 3:00 | Title card | **Both:** "They catch students. We fix assignments. RedPen." |

**Backup plan:** if a live run is slow or hits the quota, use demo mode (the saved runs replay instantly). Speed up waiting parts (2–4x) and label them "sped up".

**Don't say:** "real APU briefs" about the 5 sample ones (DSA201, BET150, DBS202, DAN301, SEP310), or "lecturer-marked" (our reference marks are an independent AI marker's).
