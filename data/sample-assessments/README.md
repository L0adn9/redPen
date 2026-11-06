# Sample assessments (synthetic)

These are 5 synthetic, APU-style assessments for building and testing RedPen. **They are not official APU assessments.** The real pilot uses 10–20 real briefs, anonymised and used with a lecturer's permission (see `data/pilot/README.md`).

Before uploading, replace `REPLACE_WITH_TEST_LECTURER_EMAIL` in each `brief.txt` with the email that should receive the approval and report (use one of your own accounts for testing).

Upload each one to Drive as `/RedPen/Assessments/<MODULE>/<ASSESSMENT>/` with the 3 files. Upload **brief.txt last**, because it fires the Drive event trigger.

| Folder | What it is | Why it's in the set | Expected exposure |
|---|---|---|---|
| `DSA201/A1` | Generic algorithms report + code | Classic take-home; generic scenario | **HIGH** (likely hero candidate) |
| `BET150/A1` | Ethics essay on the gig economy in Malaysia | Essay with no verification | **HIGH** |
| `DBS202/A1` | ERD, normalisation, SQL + reflection on a tutorial review | Specific business rules + a reflection tied to an in-class review | **MEDIUM** (AI does the ERD/SQL well; the reflection should fail) |
| `SEP310/A2` | Portfolio built on commits, signed minutes, Week 8 feedback | Process evidence, verifiable records | **LOW** |
| `DAN301/A2` | Lab with a per-student dataset, supervised part, walkthrough with a live change | Secure-lane design | **LOW** |

If the results differ a lot from "Expected", check the Examiner first (rule 4 on verifiable evidence). The spread across HIGH, MEDIUM and LOW is what makes the demo and the chat agent ("which CLOs are at risk?") interesting.
