#!/usr/bin/env python3
"""Calibration: does RedPen's Examiner mark like a reference marker?

For each already-marked student answer, runs Intake (once per brief) + the EXACT Examiner instructions
from agents/audit/05-examiner.md, then compares the Examiner's marks with the reference marks.

Folder layout (keep real work OUT of git: data/real/ is gitignored):
    data/real/calibration/
      DSA201_A1/                  <- one folder per assignment brief
        brief.txt|pdf|docx        (required)
        rubric.txt|pdf|docx       (required)
        clo-map.txt               (optional)
        S1/                       <- one folder per marked student answer
          answer.txt|pdf|docx
          marks.csv               criterion,max,mark   (reference marks per criterion)
                                  or a single line   TOTAL,100,72   if only the total is known
        S2/ ...
      reference-marker.txt        (optional) who gave the reference marks, e.g. "lecturer" or "Claude (cross-model)"

Usage:
    python3 tools/calibrate.py data/real/calibration                 # round 1
    python3 tools/calibrate.py data/real/calibration --round 2       # after tightening 05-examiner.md

Writes data/calibration/results-round<N>.csv (marks only, no student text) and prints the deck line.
Student IDs (TP numbers) and emails are masked before anything is sent. Remove names yourself.
"""
import argparse
import csv
import difflib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from redpen_audit import api_key, call, instructions, parse  # noqa: E402
from check_verdict import grade_for  # noqa: E402

GRADES = ["F", "D", "C", "C+", "B", "B+", "A", "A+"]
CALIBRATION_NOTE = (
    "CALIBRATION RUN. Instead of three AI personas, this is ONE real student's submission, given under "
    "\"student\". Mark it with exactly the same rules. Mark every rubric criterion the submission is "
    "meant to cover (all tasks), not only the selected_tasks. Return \"results\" with a single entry whose "
    "\"persona\" is \"student\".")


def read_doc(stem_dir, stem):
    for ext in (".txt", ".md", ".pdf", ".docx"):
        p = stem_dir / f"{stem}{ext}"
        if not p.exists():
            continue
        if ext == ".pdf":
            return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True,
                                  text=True, check=True).stdout
        if ext == ".docx":
            import docx
            d = docx.Document(str(p))
            out = [para.text for para in d.paragraphs]
            for t in d.tables:
                out += [" | ".join(c.text for c in row.cells) for row in t.rows]
            return "\n".join(out)
        return p.read_text(encoding="utf-8", errors="replace")
    return None


def mask(text):
    text = re.sub(r"\bTP\s?\d{5,7}\b", "[STUDENT-ID]", text, flags=re.I)
    return re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[EMAIL]", text)


def read_marks(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.reader(f):
            if not r or r[0].strip().lower() in ("criterion", ""):
                continue
            rows.append({"criterion": r[0].strip(), "max": float(r[1]), "mark": float(r[2])})
    return rows


def match(name, options):
    norm = {o.lower().strip(): o for o in options}
    hit = difflib.get_close_matches(name.lower().strip(), list(norm), n=1, cutoff=0.5)
    return norm[hit[0]] if hit else None


def pct(rows, key="mark"):
    mx = sum(r["max"] for r in rows)
    return round(100 * sum(r[key] for r in rows) / mx) if mx else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="calibration folder (see layout above)")
    ap.add_argument("--round", type=int, default=1)
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    key = api_key()
    marker = (root / "reference-marker.txt").read_text().strip() if (root / "reference-marker.txt").exists() \
        else "reference marker"
    raw_dir = root / f"_examiner-round{a.round}"
    raw_dir.mkdir(exist_ok=True)

    csv_rows, summary = [], []
    for adir in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")):
        brief, rubric = read_doc(adir, "brief"), read_doc(adir, "rubric")
        if not brief or not rubric:
            print(f"skip {adir.name}: needs brief.* and rubric.*")
            continue
        clo = read_doc(adir, "clo-map") or "(no CLO map given)"
        intake_file = raw_dir / f"{adir.name}_intake.json"
        if intake_file.exists():
            intake = json.loads(intake_file.read_text())
        else:
            text, _ = call(instructions("01-intake.md"), "\n\n".join(
                [f"===== brief =====\n{mask(brief)}", f"===== rubric =====\n{mask(rubric)}",
                 f"===== clo-map =====\n{clo}"]), key)
            intake, _ = parse(text, "intake")
            intake_file.write_text(json.dumps(intake, indent=2, ensure_ascii=False))
        print(f"{adir.name}: intake ok ({len(intake.get('rubric', []))} criteria)")

        for sdir in sorted(p for p in adir.iterdir() if p.is_dir()):
            answer = read_doc(sdir, "answer")
            if not answer or not (sdir / "marks.csv").exists():
                print(f"  skip {sdir.name}: needs answer.* and marks.csv")
                continue
            ref = read_marks(sdir / "marks.csv")
            out_file = raw_dir / f"{adir.name}_{sdir.name}_examiner.json"
            if out_file.exists():
                ex = json.loads(out_file.read_text())
            else:
                user = json.dumps({"intake": intake, "student": {"persona": "student", "answers": [
                    {"task_id": "ALL", "answer": mask(answer)}]}}, ensure_ascii=False)
                text, model = call(instructions("05-examiner.md"), user + "\n\n" + CALIBRATION_NOTE, key)
                ex, _ = parse(text, "examiner")
                ex["_model"] = model
                out_file.write_text(json.dumps(ex, indent=2, ensure_ascii=False))
            res = (ex.get("results") or [{}])[0]
            scores = res.get("scores", [])
            ex_rows = [{"criterion": s["criterion"], "max": float(s["max"]), "mark": float(s["score"])}
                       for s in scores]

            only_total = len(ref) == 1 and ref[0]["criterion"].upper() == "TOTAL"
            if only_total:
                ref_pct = round(100 * ref[0]["mark"] / ref[0]["max"])
            else:
                ref_pct = pct(ref)
                ex_by = {r["criterion"]: r for r in ex_rows}
                for r in ref:
                    m = match(r["criterion"], ex_by)
                    csv_rows.append({"sample_id": f"{adir.name}/{sdir.name}", "module": adir.name.split("_")[0],
                                     "assessment": "_".join(adir.name.split("_")[1:]), "criterion": r["criterion"],
                                     "max": r["max"], "reference_mark": r["mark"],
                                     f"examiner_mark_round{a.round}": ex_by[m]["mark"] if m else "",
                                     "notes": "" if m else "criterion not found in Examiner output"})
            if only_total or not ex_rows:
                ex_pct = pct(ex_rows) if ex_rows else res.get("total_percent", 0)
            else:  # compare like for like: only the criteria the reference marker marked
                hit = [ex_by[m] for m in (match(r["criterion"], ex_by) for r in ref) if m]
                ex_pct = round(100 * sum(h["mark"] for h in hit) / sum(r["max"] for r in ref)) if hit else 0
            g_ref, g_ex = grade_for(ref_pct), grade_for(ex_pct)
            band_gap = abs(GRADES.index(g_ref) - GRADES.index(g_ex))
            summary.append({"sample": f"{adir.name}/{sdir.name}", "ref_pct": ref_pct, "ex_pct": ex_pct,
                            "ref_grade": g_ref, "ex_grade": g_ex, "band_gap": band_gap})
            print(f"  {sdir.name}: {marker} {ref_pct}% {g_ref}  vs  Examiner {ex_pct}% {g_ex}  "
                  f"({'within one grade' if band_gap <= 1 else f'{band_gap} grades apart'})")

    if not summary:
        sys.exit("no samples found")
    out = ROOT / "data" / "calibration" / f"results-round{a.round}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample", "reference_marker", "reference_pct", "reference_grade", "examiner_pct",
                    "examiner_grade", "grade_bands_apart"])
        for s in summary:
            w.writerow([s["sample"], marker, s["ref_pct"], s["ref_grade"], s["ex_pct"], s["ex_grade"], s["band_gap"]])
    if csv_rows:
        crit_out = out.with_name(f"results-round{a.round}-criteria.csv")
        with open(crit_out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
            w.writeheader()
            w.writerows(csv_rows)

    n = len(summary)
    within = sum(s["band_gap"] <= 1 for s in summary)
    exact = sum(s["band_gap"] == 0 for s in summary)
    mad = round(sum(abs(s["ref_pct"] - s["ex_pct"]) for s in summary) / n, 1)
    bias = round(sum(s["ex_pct"] - s["ref_pct"] for s in summary) / n, 1)
    print(f"\nSaved {out.relative_to(ROOT)}")
    print(f"Round {a.round}: {within} of {n} within one grade band ({exact} same grade), "
          f"mean difference {mad} percentage points, Examiner {'higher' if bias > 0 else 'lower'} "
          f"by {abs(bias)} on average.")
    print(f'Deck line: "We checked RedPen\'s Examiner against {marker} marks on {n} marked assignments: '
          f'{within} of {n} within one grade band, mean difference {mad} points."')
    if n - within > n / 5:
        print("More than 1 in 5 off by over one band: tighten 05-examiner.md rule 2 and run --round 2.")


if __name__ == "__main__":
    main()
