#!/usr/bin/env python3
"""Check RedPen verdict files against the contract in agents/verdict-format.md.

Usage:
  python3 tools/check_verdict.py data/fake-verdicts/*.json
  python3 tools/check_verdict.py -        # paste JSON on stdin (copied from Drive), then Ctrl-D

Exit code 0 = all files valid, 1 = at least one problem found.
"""
import json
import re
import sys

GRADES = {"A+", "A", "B+", "B", "C+", "C", "D", "F"}
PERSONAS = ("copy_paster", "prompt_engineer", "honest_helper")
REQUIRED = {
    "module": str, "module_name": str, "assessment": str, "brief_path": str,
    "lecturer_email": str, "model": str, "audit_date": str, "exposure": str,
    "persona_grades": dict, "persona_totals": dict, "pass_mark": (int, float),
    "clos_at_risk": list, "easy_criteria": list, "summary": str,
}
OPTIONAL = {"file_name"}


def grade_for(pct):
    for floor, g in ((80, "A+"), (75, "A"), (70, "B+"), (65, "B"), (60, "C+"), (50, "C"), (40, "D")):
        if pct >= floor:
            return g
    return "F"


def check(v):
    errs, warns = [], []
    if not isinstance(v, dict):
        return ["top level is not a JSON object"], warns

    for key, typ in REQUIRED.items():
        if key not in v:
            errs.append(f"missing field '{key}'")
        elif not isinstance(v[key], typ) or isinstance(v[key], bool):
            errs.append(f"'{key}' has the wrong type ({type(v[key]).__name__})")
    for key in v:
        if key not in REQUIRED and key not in OPTIONAL:
            warns.append(f"extra field '{key}' (the Fix workflow ignores it)")
    if errs:
        return errs, warns

    if v["exposure"] not in ("HIGH", "MEDIUM", "LOW"):
        errs.append(f"exposure must be HIGH/MEDIUM/LOW in uppercase, got {v['exposure']!r}")
    if v["model"] not in ("flash", "pro"):
        errs.append(f"model must be 'flash' or 'pro', got {v['model']!r}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v["audit_date"]):
        errs.append(f"audit_date must be YYYY-MM-DD, got {v['audit_date']!r}")
    if not v["brief_path"].startswith("/RedPen/Assessments/"):
        warns.append("brief_path does not start with /RedPen/Assessments/")
    if "@" not in v["lecturer_email"]:
        warns.append(f"lecturer_email looks unset: {v['lecturer_email']!r}")

    for p in PERSONAS:
        g = v["persona_grades"].get(p)
        t = v["persona_totals"].get(p)
        if g not in GRADES:
            errs.append(f"persona_grades.{p} = {g!r} is not on the grade scale {sorted(GRADES)}")
        if not isinstance(t, (int, float)) or isinstance(t, bool) or not 0 <= t <= 100:
            errs.append(f"persona_totals.{p} = {t!r} must be a percentage 0-100")
        elif g in GRADES and grade_for(t) != g:
            warns.append(f"{p}: {t}% should be grade {grade_for(t)}, file says {g}")

    # Exposure must follow the Verdict rules from the totals.
    totals, pm = v["persona_totals"], v["pass_mark"]
    if all(isinstance(totals.get(p), (int, float)) for p in PERSONAS[:2]):
        expected = ("HIGH" if totals["copy_paster"] >= pm
                    else "MEDIUM" if totals["prompt_engineer"] >= pm else "LOW")
        if v["exposure"] != expected:
            errs.append(f"exposure is {v['exposure']} but totals + pass mark give {expected}")

    if v["exposure"] == "LOW" and v["clos_at_risk"]:
        errs.append("exposure is LOW, so clos_at_risk must be []")
    for i, c in enumerate(v["clos_at_risk"]):
        if not isinstance(c, dict) or set(c) != {"id", "text", "why"}:
            errs.append(f"clos_at_risk[{i}] must have exactly id, text, why")
        elif not re.fullmatch(r"CLO\d+", c["id"]):
            errs.append(f"clos_at_risk[{i}].id should look like CLO2, got {c['id']!r}")
    if not all(isinstance(c, str) for c in v["easy_criteria"]):
        errs.append("easy_criteria must be a list of strings")

    fn = v.get("file_name")
    if fn:
        want = f"{v['module']}_{v['assessment']}_{v['model']}_{v['audit_date'].replace('-', '')}.json"
        if fn != want:
            warns.append(f"file_name {fn!r} should be {want!r}")
    return errs, warns


def load(path):
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    text = text.strip()
    if text.startswith("```"):
        raise ValueError("starts with a markdown fence (```), the agent must output plain JSON")
    return json.loads(text)


def main(paths):
    if not paths:
        print(__doc__)
        return 1
    bad = 0
    for path in paths:
        try:
            errs, warns = check(load(path))
        except (ValueError, OSError) as e:
            errs, warns = [f"cannot read: {e}"], []
        status = "OK  " if not errs else "FAIL"
        bad += bool(errs)
        print(f"{status} {path}")
        for e in errs:
            print(f"   ✗ {e}")
        for w in warns:
            print(f"   ! {w}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
