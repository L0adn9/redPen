# Day-1 capability checklist (fill in on Fri)

Run these the moment the license works. Write the result and the date. If a check fails, use the fallback; don't spend more than 1 hour on any single item.

| # | Owner | Check | Result (✅/❌ + note) | If it fails |
|---|---|---|---|---|
| 1 | Abdullah | Workflow Builder + chat agents + model selector enabled in Feature management | | Ask Cindy/Marcus |
| 2 | Abdullah | Drive **event trigger** fires on a new file in a folder | | Manual trigger (@mention) for the demo |
| 3 | Hassan | **Approval** step pauses and shows "Needs review" | | Gmail "reply APPROVE" stand-in |
| 4 | Hassan | Jira Cloud connector: **search + create + update issue** with labels | | Drive upload as the register |
| 5 | Hassan | Drive **upload/create file** with content we choose | | Gmail attachment / Gmail body |
| 6 | Hassan | Sheets **update cells / insert row** exists | | Keep Jira as the register |
| 7 | Hassan | Docs **create/update** exists | | Upload a .txt revised brief to Drive |
| 8 | Abdullah | Model selector offers **Flash and Pro** per agent step | | Compare 2 personas instead |
| 9 | Abdullah | A 3-persona run finishes without timing out | | Fewer tasks, or split into 2 workflows |
| 10 | Abdullah | A scheduled run can process **several** briefs (loop) | | Monthly run audits the top 3 due soonest; demo on 1 |
| 11 | Both | Do write actions also pause for review in **scheduled/event** runs? | | Fine for the demo (human in the loop); say so in the pitch |
| 12 | Both | Can agents/workflows be **shared** between our two accounts? | | Rebuild in the leader's account from the repo prompts |
| 13 | Abdullah | **Step scope:** can a later step (e.g. the Examiner) use the output of *any* earlier step (Intake + all 3 personas), or only the step just before it? Test: in step 3, ask "repeat the module code from step 1". The docs don't say. | | Switch to pass-through mode: `agents/audit/fallback-pass-through.md` |
| 14 | Abdullah | **Event payload:** with a Drive event trigger, how does the first step see the new file (name, path, folder)? Check what the Intake step receives. | | Manual trigger with the folder path input for the demo; event trigger only shown starting a run |
| 15 | Abdullah | **Date:** does the Verdict agent write the correct `audit_date`, or a made-up one? | | Hard-code the date in the Verdict prompt on demo day, or drop the date from `file_name` and let Drive's timestamp do it |
