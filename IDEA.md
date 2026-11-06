# RedPen: an AI red-team for university assessments

> "Before your students try to get AI to do the assignment, RedPen already has, and it tells you which learning outcomes you can no longer trust."

**Team:** 2 people · **Deadline:** submit **Tue 10 Nov 2026, by the afternoon** (the team leader submits; this locks the entry)
**Theme:** 2 (Intelligent Automation & Digital Transformation), with links to 3 (data-driven decision making)

---

## 1. Problem
- GenAI can now complete many university assignments at a passing grade.
- Lecturers find out which assessments are exposed at marking time, which is too late.
- Worse, a passing AI submission means **the assessment no longer proves the student achieved the course learning outcomes (CLOs)** it was mapped to.
  - MQA (the Malaysian regulator) requires assessment to be aligned with the learning outcomes, with CLOs mapped to programme learning outcomes (PLOs) (COPPA 2nd ed.). APU's programmes publish their PLOs.
  - APU's QAA (UK) accreditation runs five years "subject to a satisfactory mid-cycle review", and APU says that review is due by 2027.
  - Unreliable CLO evidence is therefore an **accreditation risk for the whole university**, not just one lecturer's headache.
- Redesigning assessments is manual and inconsistent, and never finished: every stronger model makes last semester's "safe" assessment unsafe again.

## 2. Positioning vs. the competition
Another team is building **"Prove It"**, which **detects** AI use *after students submit*.
- RedPen does **prevention**: it fixes the assignment *before it's released*.
- Detection is reactive, contested and adversarial, and it means misconduct cases.
- Prevention is proactive, and it protects the CLO evidence the university reports to regulators.
- The two approaches complement each other, but prevention is the cheaper place to intervene.

Use this line in the pitch: *"They catch students. We fix assignments."*

## 3. How it works (Gemini Enterprise Workflow Builder)
```
Trigger: Drive event (new file in /Assessments/<module>/)  +  Schedule: monthly re-audit (1st Mon, 09:00 MYT)
 ├─ Step 1  Intake agent (Drive): brief + rubric + CLO mapping → JSON
 │          {module, assessment, CLOs tested [CLO1..n], tasks[], marks weighting, rubric criteria}
 │          → picks the 2–3 tasks worth the most marks for the attempts (keeps runs under timeout limits)
 ├─ Step 2  Persona attempts on those tasks (3 Gemini Agent steps):
 │          • Copy-paster: brief pasted straight in, no edits
 │          • Prompt engineer: multi-step, strategic AI use
 │          • Honest + AI helper: AI only as the brief permits
 ├─ Step 3  Examiner agent: grades each attempt strictly against the rubric → JSON scores + justification
 │          (coding tasks are assessed by reading the code against the rubric, NOT by running it; we say so openly)
 ├─ Step 4  Verdict agent:
 │          • AI-Exposure: HIGH (copy-paster passes) / MEDIUM (only the prompt engineer passes) / LOW
 │          • **CLOs no longer reliably evidenced** (e.g. "CLO2: Apply sorting algorithms is NOT reliably proven")
 │          • which rubric criteria the AI met easily
 ├─ Condition: exposure ≥ MEDIUM ?
 │     └─ Redesign agent: 2–3 redesigns that **must still test the same CLOs**, mapped to AIAS levels / the two-lane model
 │        (viva checkpoint, APU-local data, process evidence, in-class component, personal reflection)
 ├─ Approval step: the module lecturer approves / requests changes   ← added by hand in the builder
 └─ Actions (only actions Google documents as confirmed):
       • Jira Cloud: create / update the issue "<module> <assessment>". **Jira is the Assessment Exposure Register**
         (fields/labels: module, exposure level, CLOs at risk, model used, status). The board gives the heatmap view.
       • Drive: upload the revised brief next to the original
       • Gmail: send the verdict report to the lecturer
       • Calendar: book a 30-min review with the T&L centre if HIGH
```
**The chat agent** works over the Jira register and the Drive briefs. Lecturers and programme leaders can ask:
- "Which CLOs in my programme are at risk?"
- "Which of my Semester 2 assessments are HIGH?"
- "Why did the AI pass criterion 3?"
- "Redesign A2 for AIAS level 2, still testing CLO3."

**Why it runs monthly:** Gemini Enterprise has no "new model released" trigger, so a monthly scheduled re-audit is the honest version. It re-tests the whole bank with the strongest available model and flags any assessment whose exposure went **up**.

## 4. Connectors
- **Google (1P):** Drive (event trigger, briefs, revised briefs), Gmail, Calendar.
- **Third-party (3P):** **Jira Cloud** (register + redesign tracking; free tier).
- **Built-in:** Deep Research (current assessment-policy context for the redesign agent), Gemini Notebook (deck/mind map).
- **Optional, only if the day-1 checklist passes:** Sheets register / Docs revised brief (the docs list these write actions, but they are new), SharePoint/OneDrive, custom MCP (blocked by org policy by default).

## 5. Trust: "isn't this just AI grading AI?"
- **Calibration:** run the Examiner agent on **3–5 assignments a lecturer has already marked**.
  - Report agreement in the deck, e.g. "4 of 5 within one grade band, mean difference X marks".
  - If agreement is weak, tighten the rubric prompt and re-run. Report both rounds honestly.
- The lecturer approves every redesign, and RedPen never sees student submissions or student data.
- Every verdict cites the rubric criteria and the AI attempt it's based on.

## 6. Day-1 capability checklist (do this the moment the license works)
| # | Check | If it fails |
|---|---|---|
| 1 | Workflow Builder + chat agents enabled in Feature management | Ask Cindy/Marcus |
| 2 | Drive **event trigger** fires on a new file in a folder | Use Manual trigger (@mention) for the demo |
| 3 | **Approval** step pauses and shows "Needs Review" | Use Gmail "reply APPROVE" as a stand-in |
| 4 | Jira Cloud connector: **create + update issue** with labels | Drive upload as the register |
| 5 | Drive **upload/create file** works | Gmail attachment |
| 6 | Sheets **update cells / insert row** works | Keep Jira as the register |
| 7 | Docs **update** works | Upload a revised brief file to Drive |
| 8 | Model selector offers both **Flash and Pro** in agent steps | Compare 2 personas instead |
| 9 | A 3-persona run finishes without timing out | Fewer tasks, or split into 2 workflows |

## 7. Impact evidence to collect
- **Pilot:** 10–20 real APU briefs (our own past ones, anonymised; ask a lecturer's permission).
  - Headline: "X of 20 were passable by AI with zero effort; Y CLOs across Z modules no longer reliably evidenced."
- **Calibration result** (section 5).
- **Time:** a manual audit + redesign of one assessment (ask 2–3 lecturers) vs RedPen (minutes).
- **Flash vs Pro:** the same assignment gets e.g. C with Flash and B+ with Pro. This is the evidence for monthly re-audits.
- **Rollout:**
  - 3 months: one programme's full assessment bank audited before the semester.
  - 6 months: every programme, plus the first monthly re-audit trend.
- A quote from at least one lecturer or programme leader who tried it.

## 8. 3-minute demo script
1. **0:00 Hook:** "This is a real APU assignment. Watch what happens when it lands in Drive."
2. **0:15** Upload it. The workflow fires, and the 3 personas attempt the top-mark tasks.
3. **0:45** The Examiner gives the copy-paster a B+. Verdict: **HIGH**, and **CLO2 and CLO3 are no longer reliably proven**.
4. **1:05** **Second wow moment:** the same assignment with Flash scored a C, and with Pro a B+. "Every model release makes this worse. That's why RedPen re-audits monthly."
5. **1:25** The redesign proposals keep the same CLOs. The lecturer approves on screen.
6. **1:45** What it produced: a Jira register issue, a revised brief in Drive, an email, and a calendar invite.
7. **2:05** Chat: "Which CLOs in my programme are at risk?" Then the Jira board view.
8. **2:25** Trust and impact: the calibration score, the pilot stats, and the 3/6-month rollout.
   - Close: "They catch students. We fix assignments. Every university, every semester."

## 9. Plan for 2 people, A and B (today is Thu 5 Nov)
| Day | A (agents / Gemini Enterprise) | B (data / evidence / docs) |
|---|---|---|
| **Thu 5** | Get the license working; run the **day-1 checklist** | Collect 10–20 briefs + rubrics + CLO mappings; ask a lecturer for 3–5 marked samples; set up the Jira Cloud site |
| **Fri 6** | Build the linear path: Intake → Personas → Examiner → Verdict (manual trigger) | Connect Jira to Gemini Enterprise; Drive folder structure; start the fact-check list (§10) |
| **Sat 7** | Add the Condition, Redesign, **Approval** (by hand), actions, Drive trigger | Run the calibration (§5); prompt-tune the Examiner with A |
| **Sun 8** | Chat agent over Jira + Drive; monthly schedule; Flash vs Pro run | Full pilot run; compile the stats; Antigravity: architecture diagram + README draft |
| **Mon 9** | Freeze the build; rehearse the demo; record the 3–4 min video | Deck (Gemini Notebook → refine → **PDF ≤10 MB**); finish the README (problem, solution, research, teamwork, impact, time spent) |
| **Tue 10 AM** | Buffer: fix whatever broke; re-record if needed | Final fact-check; the leader **submits by early afternoon** (title, challenge, summary ≥50 chars, HTTPS repo, PDF, demo link) |

**Antigravity usage to document:** generate the brief/rubric sample set and the README; draw the architecture diagram; troubleshoot the Jira connector setup; optionally host an exposure-heatmap page on Cloud Run if credits exist.

## 10. Fact-check results (checked against primary sources, 5 Nov 2026)
Use the **citable wording** column exactly as given. Don't upgrade "partly true" claims in the deck.

| # | Claim | Verdict | Citable wording | Source |
|---|---|---|---|---|
| 1 | Malaysian lecturers report a surge in AI-written work | ⚠️ PARTLY | The "sharp increase" comes from an **advocacy group (MCCA) passing on lecturer feedback**, not from data: *"The MCCA has received a great deal of direct feedback from lecturers reporting a sharp increase in students submitting assignments almost entirely generated by AI."* (Siraj Jalil, MCCA; Bernama, 26 Jun 2025). The Star (23 Mar 2025) is an opinion column: "increasingly common in Malaysian universities". | [Borneo Post (Bernama syndicated)](https://www.theborneopost.com/2025/08/10/balancing-ai-benefits-academic-integrity/) · [The Star](https://www.thestar.com.my/news/education/2025/03/23/brain-vs-bot) |
| 2 | Sydney two-lane approach | ✅ | Announced 27 Nov 2024. Default switched to AI-allowed in Sem 1 2025; the **two-lane approach started in Semester 2 2025**. | [sydney.edu.au](https://www.sydney.edu.au/news-opinion/news/2024/11/27/university-of-sydney-ai-assessment-policy.html) |
| 3 | Bath two-lane from 2026/27 | ✅ | "the two-lane framework will replace the ABC categorisations from **September 2026**". Bath calls the lanes **"closed" and "open"**. | [Bath FAQ](https://teachinghub.bath.ac.uk/guide/the-two-lane-approach-frequently-asked-questions/) |
| 4 | AUT two-lane | ⚠️ PARTLY | "AUT has **adopted and adapted** the University of Sydney's two-lane model". Its lanes are **"Channel 1 / Channel 2"**. | [aut.ac.nz](https://aut.ac.nz/about/teaching-learning-and-assessment/generative-ai-and-assessment-at-aut) |
| 5 | AI Assessment Scale (AIAS) | ✅ | 5 levels (AIAS 2.1): 1 No AI · 2 AI Planning · 3 AI Collaboration · 4 Full AI · 5 AI Exploration. Cite: Perkins, Roe & Furze (2025), *JUTLP* 22(7), doi:10.53761/rrm4y757. | [aiassessmentscale.com](https://aiassessmentscale.com/) · [arXiv](https://arxiv.org/abs/2412.09029) |
| 6 | APU QAA accreditation + mid-cycle review | ✅ | Accredited May 2024. QAA: "valid for five years, subject to a satisfactory mid-cycle review". APU: "a mid-cycle review will take place by 2027". | [qaa.ac.uk](https://www.qaa.ac.uk/news-events/news/asia-pacific-university-of-technology-and-innovation-receives-global-quality-accreditation) · [apu.edu.my](https://apu.edu.my/node/738) |
| 7 | APU OBE / CLO-PLO reporting to MQA | ⚠️ PARTLY | Say: **"MQA requires assessment aligned to learning outcomes with CLO→PLO mapping (COPPA); APU programmes publish PEOs/PLOs."** Don't describe an APU-internal process unless we get an APU document. | [MQA COPPA 2nd ed.](https://www2.mqa.gov.my/qad/v2/2021/June/COPPA%202nd%20Ed%20110621.pdf) |
| 8 | DMU dual-award partner with external examiners | ✅ | DMU validates APU programmes "under the approved Dual Degree partnership", and its external examining policy covers TNE partners. | [dmu.ac.uk partner page](https://www.dmu.ac.uk/community/global-partnerships-unit/partners/apu.aspx) |

**Strongest pitch facts:** #2, #5 and #6 (the 2027 QAA mid-cycle review is our "why now").
**Gap to fill ourselves:** there's no hard Malaysian data on AI misuse, so **our own pilot stat** ("X of 20 APU briefs passable by AI") becomes the key local evidence.

## Backup idea: PactWatch
A monthly MoU / industry-partnership agent. It flags agreements that are dormant, near expiry, or have unkept promises ("promised internships: 0 placed, renewal in 58 days"). It drafts a re-engagement email for approval, then updates Jira and Calendar.
