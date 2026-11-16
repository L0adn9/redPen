---
name: redpen-approve
description: The lecturer approval gate. Prepares the follow-up (Jira card text, Gmail report, Calendar invite, revised brief) for the redesign option the user chose. Use only after the user has explicitly chosen an option.
---

# RedPen approval (human in the loop)

1. Confirm the run folder and the option ID (R1, R2 or R3) **the user chose**. If they haven't chosen, show the options from `runs/<run-id>/07-redesign.json` and ask. Never choose for them.
2. Run: `../.venv/bin/python orchestrator.py approve runs/<run-id> <OPTION>`
3. Show the user what was prepared in `runs/<run-id>/outbox/`: the email subject and first lines of `email.txt`, the Jira card summary and labels from `jira-card.json`, whether `review.ics` was created (HIGH only), and the first lines of the revised brief.
4. Say clearly: **nothing was sent**. Sending for real happens in the RedPen app when a lecturer approves there.
5. Show the updated diagram in `runs/<run-id>/report.md` (the gate now shows the decision).
6. Append the task to `AG-LOG.md`.
