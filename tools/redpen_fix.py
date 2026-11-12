"""RedPen Fix side: verdict -> redesign options -> (lecturer approves) -> Jira + email + calendar invite + revised brief.

Uses the EXACT Redesign instructions from agents/fix/01-redesign.md (same text as the Gemini Enterprise step).
Every action is optional: if its secrets are missing, the app shows a preview instead of failing.

Secrets (environment or Streamlit secrets):
  JIRA_BASE_URL (https://<site>.atlassian.net), JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT (default RP)
  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, MAIL_FROM (default SMTP_USER)
"""
import base64
import datetime as dt
import json
import os
import pathlib
import re
import smtplib
import urllib.error
import urllib.parse
import urllib.request
import uuid
from email.message import EmailMessage

from redpen_audit import ROOT, AuditError, api_key, call, parse

FIX = ROOT / "agents" / "fix"
POLICY = """Assessment design guide (summary):
- AI Assessment Scale (AIAS 2.1, Perkins, Roe & Furze 2025): 1 No AI, 2 AI Planning, 3 AI Collaboration, 4 Full AI, 5 AI Exploration.
- Two-lane approach (University of Sydney, from Semester 2 2025): "secure" lane = supervised, assured assessment; "open" lane = AI allowed and scaffolded.
- Redesign techniques: in-class or invigilated component; short viva or recorded walkthrough of the student's own work; process evidence
  (drafts, version history, decision log); APU-local or class-released data; reflection tied to verifiable in-class activity;
  critique/improve an AI-generated answer."""


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def instructions(filename):
    text = (FIX / filename).read_text(encoding="utf-8")
    m = re.search(r"^## Instructions.*?^```[a-z]*\n(.*?)^```", text, re.S | re.M)
    if not m:
        raise AuditError(f"no instructions block found in {filename}")
    return m.group(1).strip()


def brief_from_intake(intake):
    """Rebuild a readable brief from the Intake JSON (for saved runs without the original file)."""
    parts = [f"{intake.get('module', '')} {intake.get('module_name', '')} - {intake.get('assessment', '')}",
             intake.get("context", ""), f"AI policy: {intake.get('ai_policy', 'not stated')}"]
    for t in intake.get("tasks", []):
        parts.append(f"{t.get('id')}: ({t.get('marks')} marks) {t.get('text')}")
    return "\n\n".join(p for p in parts if p)


def run_redesign(verdict, brief_text, key=None):
    """2-3 redesign options that keep the same CLOs. One API call."""
    key = key or api_key()
    user = json.dumps({"verdict": verdict, "original_brief": brief_text, "assessment_design_guide": POLICY},
                      ensure_ascii=False)
    text, model = call(instructions("01-redesign.md"), user, key)
    data, _ = parse(text, "redesign")
    data["_model"] = model
    return data


def option(redesign, opt_id=None):
    opts = redesign.get("options", [])
    want = opt_id or redesign.get("recommended")
    return next((o for o in opts if o.get("id") == want), opts[0] if opts else {})


def revised_brief(brief_text, verdict, opt):
    head = (f"REVISED BRIEF - {verdict.get('module')} {verdict.get('assessment')}\n"
            f"Redesign {opt.get('id')}: {opt.get('title')} (AIAS level {opt.get('aias_level')}, {opt.get('lane')} lane)\n"
            f"Approved via RedPen on {dt.date.today().isoformat()}\n" + "=" * 70 + "\n\n")
    return head + "REVISED TASK(S)\n\n" + opt.get("revised_task_text", "") + \
        "\n\n" + "=" * 70 + "\nORIGINAL BRIEF (for reference)\n\n" + brief_text


def email_subject(v):
    ids = ", ".join(c.get("id", "") for c in v.get("clos_at_risk", [])) or "no CLOs"
    return f"RedPen: {v.get('module')} {v.get('assessment')} is {v.get('exposure')} AI-exposure ({ids} at risk)"


def email_body(v, redesign, opt):
    g, t = v.get("persona_grades", {}), v.get("persona_totals", {})
    clos = "\n".join(f"- {c.get('id')}: {c.get('text')} ({c.get('why')})" for c in v.get("clos_at_risk", [])) or "- none"
    return f"""Hi,

{redesign.get('email_summary') or v.get('summary', '')}

What the AI did
- Copy-paster (pasted the brief into AI, no edits): {g.get('copy_paster')} ({t.get('copy_paster')}%)
- Prompt engineer (strategic AI use): {g.get('prompt_engineer')} ({t.get('prompt_engineer')}%)
- Honest student using AI as allowed: {g.get('honest_helper')} ({t.get('honest_helper')}%)
Pass mark: {v.get('pass_mark')}%

CLOs no longer reliably evidenced
{clos}

Approved redesign: {opt.get('title')}: AIAS level {opt.get('aias_level')}, {opt.get('lane')} lane, about +{opt.get('extra_marking_minutes_per_student')} min marking per student.
The revised brief is attached.
Jira: RP issue "{v.get('module')} {v.get('assessment')}"

RedPen is a risk signal from simulated AI attempts marked by an AI examiner calibrated against reference marks. It does not assess any real student.
"""


def next_working_day_10am():
    d = dt.date.today() + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return dt.datetime(d.year, d.month, d.day, 10, 0)


def ics_invite(v, attendee=""):
    start = next_working_day_10am()
    end = start + dt.timedelta(minutes=30)
    f = "%Y%m%dT%H%M%S"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RedPen//EN", "METHOD:REQUEST", "BEGIN:VEVENT",
             f"UID:{uuid.uuid4()}@redpen", f"DTSTAMP:{dt.datetime.utcnow().strftime(f)}Z",
             f"DTSTART;TZID=Asia/Kuala_Lumpur:{start.strftime(f)}", f"DTEND;TZID=Asia/Kuala_Lumpur:{end.strftime(f)}",
             f"SUMMARY:RedPen review: {v.get('module')} {v.get('assessment')} ({v.get('exposure')})",
             "DESCRIPTION:Review the approved assessment redesign with the T&L centre.",
             "END:VEVENT", "END:VCALENDAR"]
    if attendee:
        lines.insert(-2, f"ATTENDEE;RSVP=TRUE:mailto:{attendee}")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------- Jira (Cloud REST v3)
def jira_configured():
    return all(_env(k) for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"))


def jira_labels(v):
    labels = [f"exposure-{v.get('exposure', '').lower()}", f"model-{v.get('model', 'flash')}",
              f"module-{v.get('module', '').lower()}"]
    labels += [f"clo-{re.sub(r'[^0-9a-z]', '', c.get('id', '').lower().replace('clo', ''))}"
               for c in v.get("clos_at_risk", [])]
    return [re.sub(r"\s+", "-", x) for x in labels if not x.endswith("-")]


def jira_description(v, opt):
    g = v.get("persona_grades", {})
    lines = [f"AI-Exposure: {v.get('exposure')} (audit {v.get('audit_date')}, persona model: {v.get('model')})",
             f"Persona grades: copy-paster {g.get('copy_paster')} / prompt engineer {g.get('prompt_engineer')} / "
             f"honest helper {g.get('honest_helper')}",
             "CLOs at risk: " + ("; ".join(f"{c.get('id')}: {c.get('text')}" for c in v.get("clos_at_risk", [])) or "none"),
             "Easy criteria: " + (", ".join(v.get("easy_criteria", [])) or "none")]
    if opt:
        lines.append(f"Approved redesign: {opt.get('id')} {opt.get('title')} (AIAS level {opt.get('aias_level')}, "
                     f"{opt.get('lane')} lane, +{opt.get('extra_marking_minutes_per_student')} min marking/student)")
    return {"type": "doc", "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": ln}]} for ln in lines]}


def _jira(method, path, body=None):
    url = _env("JIRA_BASE_URL").rstrip("/") + path
    auth = base64.b64encode(f"{_env('JIRA_EMAIL')}:{_env('JIRA_API_TOKEN')}".encode()).decode()
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Basic {auth}", "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise AuditError(f"Jira {method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")


def jira_upsert(v, opt):
    """Create or update the register issue '<module> <assessment>'. Returns (issue key, browse URL, 'created'|'updated')."""
    project = _env("JIRA_PROJECT", "RP")
    summary = f"{v.get('module')} {v.get('assessment')}"
    jql = f'project = {project} AND summary ~ "\\"{summary}\\""'
    found = _jira("GET", "/rest/api/3/search/jql?" + urllib.parse.urlencode({"jql": jql, "fields": "summary"}))
    fields = {"summary": summary, "labels": jira_labels(v), "description": jira_description(v, opt)}
    issues = [i for i in found.get("issues", []) if i.get("fields", {}).get("summary") == summary]
    if issues:
        key, how = issues[0]["key"], "updated"
        _jira("PUT", f"/rest/api/3/issue/{key}", {"fields": fields})
    else:
        fields.update({"project": {"key": project}, "issuetype": {"name": "Task"}})
        key, how = _jira("POST", "/rest/api/3/issue", {"fields": fields})["key"], "created"
    try:  # move to "Approved" if the workflow has it
        tr = _jira("GET", f"/rest/api/3/issue/{key}/transitions").get("transitions", [])
        t = next((x for x in tr if x.get("name", "").lower() == "approved" or
                  x.get("to", {}).get("name", "").lower() == "approved"), None)
        if t:
            _jira("POST", f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": t["id"]}})
    except AuditError:
        pass
    return key, _env("JIRA_BASE_URL").rstrip("/") + f"/browse/{key}", how


# ---------------------------------------------------------------- Email (SMTP)
def smtp_configured():
    return all(_env(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def send_email(to, subject, body, attachments=()):
    """attachments: [(filename, bytes, mime 'type/subtype')]"""
    msg = EmailMessage()
    msg["From"] = _env("MAIL_FROM") or _env("SMTP_USER")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    for name, data, mime in attachments:
        main, sub = mime.split("/", 1)
        msg.add_attachment(data, maintype=main, subtype=sub, filename=name)
    with smtplib.SMTP(_env("SMTP_HOST"), int(_env("SMTP_PORT", "587")), timeout=30) as s:
        s.starttls()
        s.login(_env("SMTP_USER"), _env("SMTP_PASSWORD"))
        s.send_message(msg)


def demo_redesign(name):
    p = ROOT / "data" / "demo-runs" / name / "07-redesign.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def brief_for_demo(name, intake):
    """Original brief text for a saved run, if we have it in the repo; else rebuilt from the Intake JSON."""
    mod, _, ass = name.partition("_")
    for base in ("data/sample-assessments", "data/pilot-real"):
        p = ROOT / base / mod / ass / "brief.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
    return brief_from_intake(intake)
