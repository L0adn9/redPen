#!/usr/bin/env python3
"""Check a verdict produced by the Gemini Enterprise workflow against the contract, the schema and the prototype.

    python3 tools/ge_compare.py DSA201 A1            # then paste the Verdict JSON, Ctrl-D
    python3 tools/ge_compare.py CCP A1 verdict.json

Passes when: the contract is clean, the schema matches, the exposure follows the rule, and (if the prototype has a saved
run for this assessment) the exposure is the same or one level away. Single runs vary, so one level apart is a warning,
not a failure; two levels apart means something is wrong in the Gemini Enterprise build (usually step inputs).
"""
import json
import sys

import redpen_audit as ra
from check_verdict import check

LEVEL = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def compare(module, assessment, v):
    ok = True
    errs, warns = check(v)
    for e in errs:
        print(f"✗ contract: {e}")
        ok = False
    for w in warns:
        print(f"! contract: {w}")
    for e in ra.schema_errors("06-verdict", v):
        print(f"✗ schema: {e}")
        ok = False
    try:
        want = ra.expected_exposure(v.get("persona_totals", {}), float(v.get("pass_mark", 40)))
        if v.get("exposure") != want:
            print(f"✗ exposure {v.get('exposure')} breaks the rule (totals {v.get('persona_totals')} → {want})")
            ok = False
    except (TypeError, ValueError):
        print("✗ persona_totals / pass_mark are not numbers")
        ok = False

    name = next((n for n in ra.demo_runs() if n.lower() == f"{module}_{assessment}".lower()), None)
    if name:
        p = ra.load_demo(name)["verdict"]
        gap = abs(LEVEL.get(v.get("exposure"), 9) - LEVEL.get(p.get("exposure"), 9))
        print(f"Prototype ({p.get('audit_date')}): {p.get('exposure')} {p.get('persona_totals')}")
        print(f"Gemini Enterprise:           {v.get('exposure')} {v.get('persona_totals')}")
        if gap == 0:
            print("✓ same exposure as the prototype")
        elif gap == 1:
            print("! one level apart: normal run-to-run variation; re-run once to confirm")
        else:
            print("✗ two levels apart: check that the Examiner and Verdict steps receive the Intake output (check #13)")
            ok = False
        a = {c.get("id") for c in v.get("clos_at_risk", [])}
        b = {c.get("id") for c in p.get("clos_at_risk", [])}
        print(f"  CLOs at risk: GE {sorted(a)} vs prototype {sorted(b)}")
    else:
        print(f"(no prototype run saved for {module} {assessment}; contract and rule checks only)")
    print("RESULT:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    raw = open(sys.argv[3]).read() if len(sys.argv) > 3 else sys.stdin.read()
    try:
        verdict, _ = ra.parse(raw, "verdict")
    except ra.AuditError as e:
        sys.exit(f"✗ {e}")
    sys.exit(0 if compare(sys.argv[1], sys.argv[2], verdict) else 1)
