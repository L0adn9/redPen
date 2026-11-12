# How we used Google Antigravity

Antigravity is Google's agentic IDE: you give its agent a task in plain English and it reads the repo, plans, edits files and runs commands, with each change shown for review before it lands. We opened the `redPen` repo in it and used it on real parts of the prototype. Every change it made is in the repo.

| # | Date | Who | What we asked Antigravity | What it produced | Screenshots |
|---|---|---|---|---|---|
| 1 | 13 Nov | Hassan | Explain how `streamlit_app.py`, `tools/redpen_audit.py` and `tools/redpen_fix.py` work together, from a lecturer uploading a brief to the Jira card (read-only) | A correct 6-step walkthrough in 36 s: upload, Intake, 3 AI students, Examiner, Verdict, Redesign, lecturer approval, Jira create/update. We used it to check our own architecture description. | [task1](2026-11-13_hassan_task1-explain-architecture.png) |
| 2 | 13 Nov | Hassan | Add a button under the Assessment Exposure Register that downloads the register as `redpen-register.csv` (standard library only, change nothing else) | 8 new lines in `streamlit_app.py` (+8 / −0): the **Download CSV** button now in the app. We stopped the agent while it was starting the app server, then ran the app ourselves: the button downloads all 9 audits correctly. | [code](2026-11-13_hassan_task2-csv-button-code.png) · [result](2026-11-13_hassan_task2-csv-button-result.png) |
| 3 | 13 Nov | Hassan | Add a unit test for `google_calendar_link()` (the lecturer's "Add to Google Calendar" link) and run the suite | `TestFix.test_google_calendar_link` in `tools/test_engine.py` (+12 / −0); the agent ran the suite itself: **39 tests, OK**. | [task3](2026-11-13_hassan_task3-calendar-link-test.png) |

**What we learned:** Antigravity was best at reading the whole repo quickly and at small, well-scoped changes it could verify itself (task 3 wrote and ran its own test). Long-running commands such as starting a web server are better done by hand.

**Final build (17 Nov, if shortlisted):** we plan to use Antigravity to debug the Jira Cloud connector setup in Gemini Enterprise, as shown in the briefing.
