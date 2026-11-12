"""RedPen monthly re-audit: the scheduled half of the RedPen Audit workflow.

Every stronger model can make last month's "safe" assessment unsafe again, so RedPen re-runs the full red team
(3 AI students + Examiner + Verdict) on every assessment in the register, on a schedule, with nobody pressing a button.
For each assessment it:
  1. runs the audit again on today's Gemini model,
  2. compares the exposure with the last audit (HIGH / MEDIUM / LOW),
  3. updates the Jira card's labels and adds a comment with the result (creates the card if it is new),
  4. emails an alert if the exposure went UP (needs SMTP_* and REAUDIT_ALERT_EMAIL),
  5. appends the result to data/reaudit/history.json (the app's "Monthly re-audit" panel reads this file).

Runs from .github/workflows/monthly-reaudit.yml on the 1st of every month at 09:00 MYT, or by hand:
  python3 tools/reaudit.py                 # every assessment in REGISTER
  python3 tools/reaudit.py CCP_A1 DSTR_LW1 # only these
  python3 tools/reaudit.py --no-jira       # audit only, no Jira/email
Secrets: OPENROUTER_API_KEY, JIRA_*, optional SMTP_USER/SMTP_PASSWORD + REAUDIT_ALERT_EMAIL.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import sys

import redpen_audit as ra
import redpen_fix as rf

ROOT = ra.ROOT
HISTORY = ROOT / "data" / "reaudit" / "history.json"
RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

# register name -> folder with brief.txt, rubric.txt, clo-map.txt (the 4 real APU briefs from the pilot)
REGISTER = {
    "CCP_A1": "data/pilot-real/CCP/A1",
    "DSTR_LW1": "data/pilot-real/DSTR/LW1",
    "DSTR_LW2": "data/pilot-real/DSTR/LW2",
    "WAPP_GA": "data/pilot-real/WAPP/GA",
}


def myt_now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))


def next_run(after=None):
    """The next scheduled run: the 1st of next month, 09:00 MYT (cron '0 1 1 * *' in UTC)."""
    d = (after or myt_now()).date()
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return dt.datetime(y, m, 1, 9, 0)


def load_history():
    return json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"runs": []}


def previous(name, history):
    """Last known verdict for this assessment: the latest re-audit, else the saved pilot audit."""
    for run in reversed(history["runs"]):
        for r in run["results"]:
            if r["name"] == name and r.get("exposure"):
                return {"exposure": r["exposure"], "date": run["date"], "totals": r.get("totals", {})}
    v = ra.load_demo(name)["verdict"]
    return {"exposure": v.get("exposure"), "date": v.get("audit_date"), "totals": v.get("persona_totals", {})}


def change(prev, now):
    if prev == now:
        return "same"
    return "up" if RANK.get(now, 0) > RANK.get(prev, 0) else "down"


def jira_reaudit(v, prev, how, run_date, model):
    """Find or create the register card, refresh its exposure/model labels, and comment the result."""
    project = rf._env("JIRA_PROJECT", "RP")
    summary = f"{v.get('module')} {v.get('assessment')}"
    found = rf._jira("GET", "/rest/api/3/search/jql?" + rf.urllib.parse.urlencode(
        {"jql": f'project = {project} AND summary ~ "\\"{summary}\\""', "fields": "summary,labels"}))
    issues = [i for i in found.get("issues", []) if i["fields"].get("summary") == summary]
    if issues:
        key = issues[0]["key"]
        keep = [lb for lb in issues[0]["fields"].get("labels", []) if not lb.startswith(("exposure-", "model-", "clo-"))]
        labels = sorted(set(keep + rf.jira_labels(v) + ["reaudit-monthly"]))
        rf._jira("PUT", f"/rest/api/3/issue/{key}", {"fields": {"labels": labels}})
    else:
        fields = {"project": {"key": project}, "issuetype": {"name": "Task"}, "summary": summary,
                  "labels": rf.jira_labels(v) + ["reaudit-monthly"], "description": rf.jira_description(v, None)}
        key = rf._jira("POST", "/rest/api/3/issue", {"fields": fields})["key"]
    arrow = {"same": "no change", "up": "EXPOSURE WENT UP", "down": "exposure went down"}[how]
    t = v.get("persona_totals", {})
    text = (f"Monthly re-audit {run_date} ({model}): {prev} -> {v.get('exposure')} ({arrow}). "
            f"Copy-paster {t.get('copy_paster')}%, prompt engineer {t.get('prompt_engineer')}%, "
            f"honest student {t.get('honest_helper')}% (pass mark {v.get('pass_mark', 50)}%). "
            "CLOs at risk: " + (", ".join(c.get("id", "") for c in v.get("clos_at_risk", [])) or "none") +
            ". Scheduled by RedPen; no one pressed a button.")
    rf._jira("POST", f"/rest/api/3/issue/{key}/comment", {"body": {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": text}]}]}})
    return key


def audit_one(name, run_date):
    folder = ROOT / REGISTER[name]
    saved = ra.load_demo(name)["verdict"]  # keeps the module code / assessment id the register already uses
    txt = {n: (folder / n).read_text(encoding="utf-8") for n in ("brief.txt", "rubric.txt", "clo-map.txt")}
    res = ra.run_audit(txt["brief.txt"], txt["rubric.txt"], txt["clo-map.txt"], saved["module"], saved["assessment"],
                       run_date=run_date,
                       on_step=lambda n, d, s: print(f"  {name} {n}: {s}s", flush=True))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help=f"register names (default: all of {', '.join(REGISTER)})")
    ap.add_argument("--no-jira", action="store_true", help="audit only: no Jira card, no email")
    ap.add_argument("--trigger", default="manual", help="'schedule' when run by the monthly GitHub Action")
    a = ap.parse_args()
    names = a.names or list(REGISTER)
    unknown = [n for n in names if n not in REGISTER]
    if unknown:
        sys.exit(f"unknown: {unknown}; choose from {list(REGISTER)}")
    history = load_history()
    now = myt_now()
    run_date = now.date().isoformat()
    print(f"RedPen monthly re-audit {now:%Y-%m-%d %H:%M} MYT ({a.trigger}) · models: {ra.describe()}")

    results = []
    with cf.ThreadPoolExecutor(2) as ex:
        futs = {ex.submit(audit_one, n, run_date): n for n in names}
        for fut in cf.as_completed(futs):
            name = futs[fut]
            prev = previous(name, history)
            try:
                res = fut.result()
            except ra.AuditError as e:
                print(f"FAIL {name}: {e}", flush=True)
                results.append({"name": name, "error": str(e)[:300], "previous": prev["exposure"]})
                continue
            v, model = res["verdict"], res["log"]["steps"]["06-verdict"]["model"]
            how = change(prev["exposure"], v.get("exposure"))
            r = {"name": name, "assessment": f"{v.get('module')} {v.get('assessment')}",
                 "previous": prev["exposure"], "previous_date": prev["date"], "exposure": v.get("exposure"),
                 "change": how, "totals": v.get("persona_totals", {}), "model": model,
                 "clos_at_risk": [c.get("id") for c in v.get("clos_at_risk", [])]}
            if not a.no_jira and rf.jira_configured():
                try:
                    r["jira"] = jira_reaudit(v, prev["exposure"], how, run_date, model)
                except ra.AuditError as e:
                    r["jira_error"] = str(e)[:200]
            alert_to = rf._env("REAUDIT_ALERT_EMAIL")
            if how == "up" and not a.no_jira and alert_to and rf.smtp_configured():
                try:
                    rf.send_email(alert_to, f"[RedPen] AI exposure went UP: {r['assessment']} is now {v.get('exposure')}",
                                  f"This month's scheduled re-audit found that {r['assessment']} moved from "
                                  f"{prev['exposure']} to {v.get('exposure')} on {model}.\n\n"
                                  f"Persona totals: {r['totals']}\nCLOs at risk: {', '.join(r['clos_at_risk']) or 'none'}\n\n"
                                  "Open RedPen to review a redesign.\n\n-- RedPen (scheduled re-audit)")
                    r["alert_sent"] = True
                except Exception as e:  # noqa: BLE001
                    r["alert_error"] = str(e)[:200]
            print(f"DONE {name}: {prev['exposure']} -> {v.get('exposure')} ({how}) {r.get('jira', '')}", flush=True)
            results.append(r)

    results.sort(key=lambda r: names.index(r["name"]))
    history["runs"].append({"date": run_date, "time": f"{now:%H:%M} MYT", "trigger": a.trigger,
                            "models": ra.models(), "next_run": f"{next_run(now):%Y-%m-%d %H:%M} MYT",
                            "results": results})
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = sum("error" not in r for r in results)
    print(f"Saved {HISTORY.relative_to(ROOT)}: {ok}/{len(results)} re-audited. Next run {next_run(now):%d %b %Y 09:00} MYT.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
