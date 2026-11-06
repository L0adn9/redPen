# Fix workflow + Jira: build guide (Hassan)

Build in this order and test each step. Exact button names in Gemini Enterprise may differ slightly from the text below; the steps follow Google's Jira Cloud and Workflow Builder docs.

## 0. Before Gemini Enterprise (Fri)
1. **Jira Cloud (free):** sign up at atlassian.com → Jira → create a site (e.g. `redpen-apu.atlassian.net`).
   - Create a **Kanban** project named **RedPen Register**, key **`RP`**.
   - Board columns: **Audited → Redesign proposed → Approved → Released** (Board settings → Columns; add the statuses).
   - Labels are created when first used; no setup needed.
2. Confirm you're a Jira **org admin**: Jira **Settings** shows **System**. You will be, since it's your own site.
3. **Atlassian OAuth app** (Google's required steps):
   1. developer.atlassian.com → profile → **Developer console** → **Create → OAuth 2.0 integration**. Name: `RedPen Gemini`.
   2. **Authorization** → OAuth 2.0 (3LO) → **Add** → Callback URL:
      - `https://vertexaisearch.cloud.google.com/console/oauth/jira_oauth.html` (data ingestion + actions; **use this**)
      - (`https://vertexaisearch.cloud.google.com/oauth-redirect` is for federated mode only)
   3. **Distribution** → Edit → Sharing. Vendor: `Google`. Privacy policy: `https://policies.google.com`. "Stores personal data?" → **Yes**, and tick the personal-data-reporting confirmation.
   4. **Permissions** → Jira API → Add → Configure:
      - Classic: `read:jira-work`, `write:jira-work`
      - Granular: `read:user:jira`, `read:group:jira`, `read:avatar:jira`, `read:issue-security-level:jira`, `read:issue-security-scheme:jira`, `read:audit-log:jira`, `write:comment:jira`, `write:issue:jira`
   5. **Settings** → copy the **Client ID** and **Client secret**. Keep them out of the repo; `.gitignore` blocks `secrets*`.
4. Create the Drive folders from `TASKS.md` → Agreements #1 if Abdullah hasn't yet. Upload `data/policy/assessment-design-guide.txt` to `/RedPen/Policy/` and the 2 fake verdicts from `data/fake-verdicts/` to `/RedPen/Verdicts/`.
   - Set `lecturer_email` in the fakes to your second email address before uploading.

## 1. Connect Jira to Gemini Enterprise (Fri evening)
1. In the RedPen app: **Connected data stores → New data store → Jira Cloud**. Enter the site URL, Client ID and secret, then authorize with your Atlassian account.
2. Turn on actions: **Search For Data** (all) + **Add Or Update Data**.
3. Wait for the first sync, then test in the app chat: "List issues in project RP".
   - Create one test issue by hand first so there's something to find.
4. **Common errors:**
   - "callback URL is invalid": the callback URL doesn't match exactly (no trailing slash).
   - Permission errors: the Google account needs the **Discovery Engine Editor** role. If you can't create the data store, ask Cindy/Marcus. That's a blocker, so tell Abdullah too.
   - Ask Antigravity: paste the error and the steps above, then screenshot the conversation for `docs/antigravity/`.
5. Message Abdullah: **"Jira connected"**.

## 2. Fix workflow on the fake verdicts (Fri night → Sat)
1. App → Agents → New → Workflow: **RedPen Fix**.
2. **Trigger:** start with **Manual** (input: verdict file path) so you can build and test fast. Switch to the event trigger at step 4.
3. Steps, from `02-condition-approval-actions.md`:
   1. (optional) "Read verdict" agent
   2. **Condition**: HIGH/MEDIUM → Redesign; LOW → log only
   3. **Redesign agent**: paste `01-redesign.md`
   4. **Approval**
   5. "Compose revised brief" agent → **Drive upload** to `/RedPen/Revised/`
   6. **Jira** search → create/update
   7. **Gmail** report
   8. **Condition** HIGH → **Calendar** event
4. Test with `DSA201_A1_pro_20261107.json` (HIGH): expect a Jira issue, revised brief, email and invite. Test with `DAN301_A2_pro_20261107.json` (LOW): expect a Jira issue labelled `exposure-low` and no redesign.
5. Message Abdullah: **"Fix workflow works on fake verdicts"**.

## 3. Event trigger (Sat)
1. Add an **Event trigger: Google Drive**, new file in `/RedPen/Verdicts/`. Turn the workflow **ON**.
2. Test: copy a fake verdict into `/Verdicts/` under a new name. The workflow should start by itself.
3. If it doesn't fire: use the Gmail fallback in `agents/verdict-format.md` (Gmail event trigger on subject `RedPen verdict`).

## 4. Sync 2: integration test with Abdullah (Sat ~9 PM)
Run the hero assignment end to end. If it breaks, decide on the fallback that night.

## 5. Pilot (Sun from 12 PM)
Follow `data/pilot/README.md`.

## Export for the repo (Mon)
Screenshot the workflow canvas, every step's settings and the Jira board into `agents/fix/screenshots/`. Copy any instruction changes back into these files.
