---
name: redpen-browser-test
description: Use the browser to test the hosted RedPen app end to end and write a short test report. Use when asked to test or check the live app.
---

# Browser test of the live app

Open https://redpen-apu.streamlit.app in the browser. **Do not enter any password and do not type any email address.**

1. Audit page: open the saved audit **CT074-3-2 A1 Concurrent Programming**. Record the exposure level and the three AI students' grades and totals.
2. Go through Verdict -> Fix -> Approve and click Approve on the recommended redesign. Record what the app says it did (it should prepare, not send, without the password).
3. Repeat step 1 for **DSTR LW1** and **WAPP** (WAPP should be LOW with no redesign).
4. Register page: check it lists 9 audits and shows the live Jira table.
5. How it works page: check it loads.
6. Write `browser-test.md` in this folder: what you clicked, what you saw (numbers), anything broken, slow or confusing, with screenshots from the recording. Compare the CT074 numbers with `../data/demo-runs/CCP_A1/06-verdict.json`.
7. Append the task to `AG-LOG.md`.
