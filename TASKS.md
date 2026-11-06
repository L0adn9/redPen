# RedPen: task split (2 people, both build, no overlap)

**Deadline:** submit **Tue 10 Nov by 3 PM MYT** (the portal closes 11:59 PM, so don't cut it close). **Registration closes Sun 8 Nov, 11:59 PM.**
**Master plan:** `IDEA.md`. This file replaces its §9 schedule.
**Repo:** https://github.com/L0adn9/redPen (currently **private and empty**; make it **public before submitting**).

**Done:** ✅ team registered · ✅ GitHub repo created · ✅ repo set up with all agent instructions + guides

**Start here:** Abdullah → [`agents/audit/00-build-guide.md`](agents/audit/00-build-guide.md) · Hassan → [`agents/fix/00-build-guide.md`](agents/fix/00-build-guide.md) · Both → [`docs/day1-checklist.md`](docs/day1-checklist.md) and [`agents/verdict-format.md`](agents/verdict-format.md)

## The idea: two workflows, connected through Drive

RedPen is built as **two separate workflows**, one per person. They only meet at a file in Drive, so neither of you ever edits the other's workflow.

```
 A = ABDULLAH: "RedPen Audit" workflow + chat    B = HASSAN: "RedPen Fix" workflow + Jira
 ─────────────────────────────────────────        ────────────────────────────────────────────
 Trigger: new brief in /Assessments/  (+ monthly)  Trigger: new file in /Verdicts/
  → Intake agent                                    → Condition: exposure ≥ MEDIUM?
  → 3 Persona agents                                → Redesign agent (same CLOs, AIAS levels)
  → Examiner agent                                  → Approval step (lecturer)
  → Verdict agent                                   → Jira create/update (the register)
  → Drive: upload verdict file to /Verdicts/  ───►  → Drive: upload revised brief to /Revised/
 "RedPen Insight" chat agent over Jira + Drive      → Gmail report + Calendar review if HIGH
```

This split is also a selling point for the pitch: two agents that hand off through Drive, so the audit and the fix can scale independently.

**Fallback if the Drive trigger between the two is flaky:** Gemini Enterprise lets you add existing agents as steps. On Sunday, A adds B's Redesign agent and actions to the end of the Audit workflow, and B's workflow stays as a manual-trigger backup.

## Who owns what (the one rule: only edit what you own)

| | **A = Abdullah: Audit + Chat** | **B = Hassan: Fix + Register** |
|---|---|---|
| **Builds** | Intake, 3 Personas, Examiner, Verdict agents; Audit workflow; Drive event trigger on `/Assessments/`; monthly schedule; Flash vs Pro; **Insight chat agent** | Jira Cloud site + connector; Redesign agent; Fix workflow (Condition, Approval, Jira, Drive, Gmail, Calendar); event trigger on `/Verdicts/` |
| **Evidence** | **Calibration** (it tunes A's own Examiner) + its numbers | **Pilot** run of 10–20 briefs + the stats; lecturer outreach + quote |
| **Presentation** | Demo video (screen recording + edit); architecture diagram; judge access | Deck (PDF ≤10 MB) + README (writing-heavy; A reviews both) |
| **Repo folders** | `/agents/audit/`, `/docs/calibration/`, `/docs/diagram/`, `/video/` | `/agents/fix/`, `/data/`, `/deck/`, `README.md` |
| **Antigravity** | Generate the 5 starter briefs/rubrics; architecture diagram | Debug the Jira connector; README draft; stats summary |

**Why this is fair:** each person builds one complete workflow plus one extra build piece (A: the chat agent; B: the Jira setup and connector, the fiddliest part). Each owns one piece of evidence and one main presentation piece. Abdullah takes the visual/technical presentation work (video, diagram); Hassan takes the writing (deck, README). Each reviews the other's presentation piece. Both get demo-able work to show the judges.

**Prompts live in the repo.** Every agent's instructions are saved as a text file in your `/agents/...` folder (the source of truth), then pasted into Gemini Enterprise. If agents can't be shared between your two accounts, you can rebuild everything in the leader's account by copy-paste in 20 minutes.

Both of you screenshot your Antigravity use into `/docs/antigravity/` (the judges want to see it).

---

## Agreements to lock first (30 min together, today)

**1. Drive structure (shared; each person only creates files in their own folders)**
```
/RedPen/
  Assessments/<MODULE>/<ASSESSMENT>/   brief.pdf · rubric.pdf · clo-map.txt      ← A adds starter set, B adds the pilot set
  Verdicts/                            ← A's workflow writes here, B's workflow reads here
  Revised/                             ← B's workflow writes here
  Calibration/                         ← A
  Policy/                              ← B (AIAS paper, Sydney/Bath pages, MQA COPPA extract; Redesign agent's knowledge)
```
`clo-map.txt`, one line per CLO: `CLO2 | Apply sorting algorithms to solve problems | tasks: T1,T3`

**2. The hand-off contract: the verdict file (the most important agreement)**
File name: `/Verdicts/<MODULE>_<ASSESSMENT>_<model>_<YYYYMMDD>.json`
```json
{
  "module": "CT046",
  "assessment": "A1",
  "brief_path": "/RedPen/Assessments/CT046/A1/brief.pdf",
  "model": "pro",
  "exposure": "HIGH",
  "persona_grades": {"copy_paster": "B+", "prompt_engineer": "A-", "honest_helper": "C"},
  "clos_at_risk": [{"id": "CLO2", "text": "Apply sorting algorithms", "why": "AI met criteria 1 and 3 with no effort"}],
  "easy_criteria": ["Algorithm explanation", "Complexity analysis"]
}
```
B can start building **before A is done** by hand-writing 2 fake verdict files (one HIGH, one LOW) and dropping them in `/Verdicts/`.

**3. Jira contract (B owns it)**
- Project key `RP`, issue type `Task`, summary `<MODULE> <ASSESSMENT>` (e.g. `CT046 A1`).
- Labels: `exposure-high|exposure-medium|exposure-low`, `clo-2`, `model-flash|model-pro`, `module-ct046`.
- Board columns: `Audited → Redesign proposed → Approved → Released`.

**4. Hero assignment:** one real APU brief that stars in the video. Pick it together by Sat noon.

---

## Working together: 4 sync points

You work independently. At each sync point, **stop your own work once you reach its "Ready when" line**, then meet. If you're ready early, move on to the next task in your column and come back at the agreed time. If you're running late, message the other person: "need 1 more hour".

### Sync 1: Kick-off. Fri 6 Nov, today (30 min)
**Ready when:** both of you have a working Gemini Enterprise login.
**Do together:**
1. Decide who's the **team leader** (only the leader submits).
2. Confirm the **Drive folders** (see Agreements #1). Abdullah creates `/RedPen/` and shares it with Hassan as Editor.
3. Read the **verdict file format** (Agreements #2) line by line, then copy it into `/agents/verdict-format.md`. This is the contract; neither of you changes it alone.
4. Confirm the **Jira labels** (Agreements #3).
5. Check you can each see the GE app. Abdullah adds Hassan as a user if needed.

**Then:** Abdullah → Intake + Persona agents. Hassan → repo, Jira, 2 fake verdict files, Redesign agent.

### Sync 2: Join the parts. Sat 7 Nov, ~9 PM (1 hour)
**Ready when:**
- **Abdullah:** his workflow takes a brief from `/Assessments/` and writes a correct verdict file into `/Verdicts/`.
- **Hassan:** his workflow takes a fake verdict from `/Verdicts/`, gets approval, and creates the Jira issue, revised brief, email and calendar invite.

**Do together:**
1. Drop the **hero assignment** into `/Assessments/` and watch it run end to end (Audit → verdict → Fix → Jira).
2. If the hand-off doesn't fire: Abdullah adds Hassan's Redesign agent + actions as steps at the end of the Audit workflow (one workflow). Decide this tonight, not Sunday.
3. Pick the **hero assignment** for the video, if not already done.
4. Write down anything broken as a short list in `/docs/bugs.md`, with an owner per bug.

**Then:** Abdullah → calibration round 1 + monthly schedule. Hassan → load the real pilot briefs.

### Sync 3: Pilot go. Sun 8 Nov, 12 PM (15 min)
**Ready when:**
- **Abdullah:** Examiner tuned after calibration round 1; Flash vs Pro works.
- **Hassan:** 10–20 real briefs with clo-maps are in `/Assessments/`.

**Do together:**
1. Agree the pilot starts now, and that from here on **only bug fixes** go into the workflows (no new features).
2. Agree the **stats you'll report** (X/20 HIGH, CLOs at risk, Flash vs Pro differences, minutes per audit, calibration agreement).
3. Check that registration is confirmed.

**Then:** Hassan runs the pilot and fixes Fix-workflow bugs. Abdullah builds the chat agent, runs calibration round 2 and fixes Audit-workflow bugs.

### Sync 4: Freeze + record. Mon 9 Nov, 12 PM (1 hour)
**Ready when:**
- **Abdullah:** chat agent works; calibration numbers in `/docs/calibration/`; architecture diagram done.
- **Hassan:** pilot stats in `/data/`; README first draft done.

**Do together:**
1. **Freeze the build.** No more changes to any agent or workflow after this.
2. Record the demo following IDEA.md §8, with Abdullah driving the screen and **both doing the voice-over**.
3. Swap: Abdullah takes the README draft to review; Hassan takes the stats to put in the deck.

**Then:** Abdullah edits the video and sets up judge access. Hassan builds the deck and finishes the README.

### Final check: Tue 10 Nov, 12 PM (30 min)
**Ready when:** video uploaded, deck PDF exported, README final.
**Do together:** go through the submission checklist at the bottom of this file in an incognito window. Then the **leader submits by 3 PM**.

---

## Things you own together (change only after talking)
- The **verdict file format** (`/agents/verdict-format.md`)
- The **Drive folder structure** and the **Jira labels**
- The **hero assignment** and the **demo script** (IDEA.md §8)
- The **project title, one-line summary and pitch line** ("They catch students. We fix assignments.")
- The **final stats** used in the deck, README and video (one set of numbers everywhere)

## "Done" messages to send each other
Send one short message when you reach each of these. That way neither of you needs to ask "is it ready?"
- Abdullah: "Verdict files are landing in /Verdicts/" · "Examiner calibrated: N of 5 within one grade" · "Chat agent live" · "Video uploaded: <link>"
- Hassan: "Jira connected" · "Fix workflow works on fake verdicts" · "Pilot briefs loaded" · "Pilot stats done" · "Deck PDF ready"

---

## Day-by-day

### Fri 6 Nov (today)
| A | B |
|---|---|
| License working; create the GE app; enable chat agents + workflows + model selector; add B as a user | ~~Register the team~~ ✅ done; decide who's leader (only the leader submits) |
| Day-1 checks **#1, 2, 8, 9, 10** (features, Drive trigger, Flash/Pro, timeouts, loops) | Day-1 checks **#3, 4, 5, 6, 7** (approval, Jira, Drive upload, Sheets, Docs) |
| Antigravity: 5 starter briefs + rubrics + clo-maps into `/Assessments/` | ~~Create the GitHub repo~~ ✅ done; add the folders above; Jira Cloud site + project `RP` |
| Build Intake → 3 Personas (manual trigger) | Connect Jira in GE; write 2 fake verdict files; start the Redesign agent |
| | Message 2–3 lecturers: ask for 10–20 past briefs, 3–5 marked samples, a 15-min chat |

### Sat 7 Nov
| A | B |
|---|---|
| Examiner + Verdict agents; upload the verdict JSON to `/Verdicts/` | Fix workflow: Condition → Redesign → **Approval** (by hand) → Jira, Drive, Gmail, Calendar |
| Drive event trigger on `/Assessments/` | Event trigger on `/Verdicts/`; test it with the fake verdicts |
| **Calibration round 1** (lecturer-marked samples vs Examiner); tune the Examiner | Load the real briefs (anonymised) + write their clo-maps |

**Sat night, integration test together (1 hour):** drop the hero brief into `/Assessments/`. Does A's verdict reach `/Verdicts/`, and does B's workflow fire and create the Jira issue? If not, use the fallback (add B's agent as a step in A's workflow).

### Sun 8 Nov
| A | B |
|---|---|
| Monthly schedule trigger; Flash vs Pro run on the hero assignment | **Pilot:** run 10–20 briefs end to end (from 12 PM); compile the stats (X/20 HIGH, CLOs at risk, minutes per audit) |
| Insight chat agent over Jira + Drive (test the 4 questions in IDEA.md §3) | Fix bugs from the pilot (in B's workflow only) |
| Calibration round 2; write up the numbers in `/docs/calibration/` | Lecturer interview + quote; start the README |
| Fix bugs from the pilot (in A's workflow only); architecture diagram | **Check registration is confirmed before 11:59 PM** |

### Mon 9 Nov
| A | B |
|---|---|
| **Both freeze the build at 12 PM** | **Both freeze the build at 12 PM** |
| Record the demo (IDEA.md §8 script, hero assignment), edit the 3–4 min video, upload it unlisted. Both of you do the voice-over together. | Deck: Gemini Notebook from the README + stats → refine → **PDF ≤ 10 MB** |
| Review B's deck and README | Review A's video cut |
| Give the judges access to the GE app; write `/docs/judge-access.md` | Finish the README: problem, solution, research, teamwork, impact, time spent |
| Export final prompts + screenshots into `/agents/audit/` | Export final prompts + screenshots into `/agents/fix/`; final fact-check (IDEA.md §10) |

### Tue 10 Nov
| A | B |
|---|---|
| Buffer: re-record a clip if needed | Buffer: fix the deck/README |
| Open the repo, PDF and video links in an incognito window | **Leader submits by 3 PM:** title, challenge (Theme 2), summary ≥50 chars, HTTPS repo, PDF, demo link |

---

## If something goes wrong
- **Any day-1 check fails:** use the fallbacks in IDEA.md §6. Don't spend more than 1 hour on any single connector.
- **The Drive hand-off between workflows doesn't trigger:** A adds B's Redesign agent + actions as steps in the Audit workflow (one workflow). B's prompts are in `/agents/fix/`, so this takes minutes.
- **Agents can't be shared between your accounts:** rebuild in the leader's account from the repo prompts.
- **The workflow is flaky on demo day:** use manual triggers, record clips separately, and edit them together.

## Submission checklist
- [x] Team registered
- [ ] Repo switched from private to **public** (judges must open the link)
- [ ] Repo public over HTTPS, with README covering the 5 points
- [ ] PDF deck ≤ 10 MB
- [ ] 3–4 min video link works logged out
- [ ] Judges can open the GE app (`/docs/judge-access.md`)
- [ ] Antigravity screenshots in `/docs/antigravity/`
- [ ] No secrets or real student data in the repo
