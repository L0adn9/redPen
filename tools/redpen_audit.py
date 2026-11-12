#!/usr/bin/env python3
"""RedPen Audit engine: brief + rubric + CLO map  ->  verdict JSON (agents/verdict-format.md).

Runs the EXACT instructions from agents/audit/0[1-6]*.md (the block under "Instructions (paste this)"):
  Intake -> 3 AI "students" (in parallel) -> Examiner -> Verdict
on the Gemini API. The same instructions are pasted into Gemini Enterprise for the final build.

Use it from the app:
    from tools.redpen_audit import run_audit, load_demo, demo_runs
    result = run_audit(brief, rubric, clo_map, module="DSA201", assessment="A1",
                       lecturer_email="x@apu.edu.my", on_step=lambda name, data, secs: ...)
    result["verdict"]          # dict, matches agents/verdict-format.md
    result["steps"]            # {"01-intake": {...}, "02-copy_paster": {...}, ... "06-verdict": {...}}
    result["log"]              # models used, seconds per step, contract check errors/warnings
    load_demo("DSA201_A1")     # same shape, from data/demo-runs/ (no API calls, instant)

Use it from the terminal:
    python3 tools/redpen_audit.py data/sample-assessments/DSA201/A1
    python3 tools/redpen_audit.py data/sample-assessments/*/* --save-demo      # refresh data/demo-runs/
    python3 tools/redpen_audit.py data/real/X/A1 --out data/real/runs           # REAL briefs: keep out of git

Needs OPENROUTER_API_KEY (preferred: paid, no daily cap, has Pro) or GEMINI_API_KEY (free AI Studio key),
in the environment, Streamlit secrets, or redPen/.env. REDPEN_BACKEND=openrouter|gemini forces one.
Models: REDPEN_MODELS = comma list tried in order; on a 429 (quota) the step moves to the next model.
The free tier gives ~20 requests/day per model and one audit = 6 requests, so the list spreads the load.
One audit takes about 3-6 minutes.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
AUDIT = ROOT / "agents" / "audit"
DEMO = ROOT / "data" / "demo-runs"
API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
DEFAULT_MODELS = "gemini-3-flash-preview,gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash"
DEFAULT_OPENROUTER_MODELS = "google/gemini-3-flash-preview,google/gemini-3.8-flash,google/gemini-3.7-flash"
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
PRO_MODEL = "google/gemini-4-argon"  # OpenRouter only; the free AI Studio key has no Pro quota
PERSONAS = {"copy_paster": "02-persona-copy-paster.md",
            "prompt_engineer": "03-persona-prompt-engineer.md",
            "honest_helper": "04-persona-honest-helper.md"}
STEP_TITLES = {"01-intake": "Intake: reading the brief, rubric and CLO map",
               "02-copy_paster": "AI student 1: copy-paster",
               "02-prompt_engineer": "AI student 2: prompt engineer",
               "02-honest_helper": "AI student 3: honest helper",
               "05-examiner": "Examiner: marking all three against the rubric",
               "06-verdict": "Verdict: exposure and CLOs at risk"}

sys.path.insert(0, str(ROOT / "tools"))
from check_verdict import check  # noqa: E402


class AuditError(RuntimeError):
    pass


def models():
    if backend() == "openrouter":
        raw = os.environ.get("REDPEN_MODELS", DEFAULT_OPENROUTER_MODELS)
        return [m if "/" in m else "google/" + m for m in (x.strip() for x in raw.split(",")) if m]
    return [m.strip() for m in os.environ.get("REDPEN_MODELS", DEFAULT_MODELS).split(",") if m.strip()]


def _env(name):
    if os.environ.get(name):
        return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip()
    return ""


def backend():
    """'openrouter' if REDPEN_BACKEND says so or an OPENROUTER_API_KEY exists (and REDPEN_BACKEND isn't 'gemini')."""
    choice = os.environ.get("REDPEN_BACKEND", "auto")
    if choice in ("openrouter", "gemini"):
        return choice
    return "openrouter" if _env("OPENROUTER_API_KEY") else "gemini"


def api_key():
    name = "OPENROUTER_API_KEY" if backend() == "openrouter" else "GEMINI_API_KEY"
    key = _env(name)
    if not key:
        raise AuditError(f"{name} not set (environment, Streamlit secrets, or redPen/.env)")
    return key


def instructions(filename):
    """The text inside the first ``` block after the 'Instructions' heading."""
    text = (AUDIT / filename).read_text(encoding="utf-8")
    m = re.search(r"^## Instructions.*?^```[a-z]*\n(.*?)^```", text, re.S | re.M)
    if not m:
        raise AuditError(f"no instructions block found in {filename}")
    return m.group(1).strip()


def _post(model, system, user, key):
    timeout = int(os.environ.get("REDPEN_TIMEOUT", "240"))
    if backend() == "openrouter":
        body = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
        }).encode()
        req = urllib.request.Request(OPENROUTER_API, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {key}",
            "X-Title": "RedPen"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        if "error" in d:
            raise KeyError(d["error"])
        return d["choices"][0]["message"]["content"] or "", d.get("model", model)
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }).encode()
    req = urllib.request.Request(API.format(model), data=body, method="POST", headers={
        "Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    parts = d["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts if not p.get("thought")), d.get("modelVersion", model)


def call(system, user, key, model_list=None):
    """One Gemini call. Moves down the model list on quota errors; retries server errors."""
    tried = []
    for rnd in range(2):  # second round after a pause, in case it was a per-minute limit
        for model in model_list or models():
            for attempt in range(3):
                try:
                    return _post(model, system, user, key)
                except urllib.error.HTTPError as e:
                    msg = e.read().decode(errors="replace")[:200]
                    if e.code == 429:
                        tried.append(f"{model}: quota")
                        break  # next model
                    if e.code in (500, 502, 503, 504) and attempt < 2:
                        time.sleep(10 * (attempt + 1))
                        continue
                    tried.append(f"{model}: HTTP {e.code} {msg}")
                    break
                except (TimeoutError, OSError) as e:  # hung or overloaded model: try the next one
                    tried.append(f"{model}: {type(e).__name__}")
                    break
                except (KeyError, IndexError) as e:  # empty or blocked answer
                    if attempt < 2:
                        continue
                    tried.append(f"{model}: {e}")
                    break
        if rnd == 0:
            time.sleep(30)
    raise AuditError("all models failed: " + "; ".join(tried))


def parse(text, step):
    """JSON from model output. Returns (data, warning or None)."""
    t = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    warn = f"{step}: output wrapped in ``` fences" if stripped != t else None
    try:
        return json.loads(stripped, strict=False), warn
    except json.JSONDecodeError as e:
        try:  # the model sometimes repeats the object: keep the first complete one
            obj, end = json.JSONDecoder(strict=False).raw_decode(stripped)
            return obj, f"{step}: ignored {len(stripped) - end} chars of extra text after the JSON"
        except json.JSONDecodeError:
            raise AuditError(f"{step} did not return valid JSON: {e}")


def run_audit(brief, rubric, clo_map, module="MODULE", assessment="A1", lecturer_email=None,
              run_date=None, model_label="flash", on_step=None, key=None, model_list=None):
    """Run the full Audit chain (6 API calls, ~3-6 min).

    on_step(step_name, data, seconds) is called after each step, on the caller's thread, in this order:
    01-intake, the three 02-<persona> steps as they finish, 05-examiner, 06-verdict.
    Step names and display titles: STEP_TITLES. Raises AuditError if every model fails.
    """
    key = key or api_key()
    run_date = run_date or dt.date.today().isoformat()
    log = {"module": module, "assessment": assessment, "run_date": run_date,
           "steps": {}, "warnings": []}
    steps = {}

    def step(name, system, user):
        t0 = time.time()
        text = version = None
        for attempt in range(2):  # one retry if the JSON is broken
            text, version = call(system, user, key, model_list)
            try:
                data, warn = parse(text, name)
                break
            except AuditError:
                if attempt == 1:
                    raise
        if warn:
            log["warnings"].append(warn)
        secs = round(time.time() - t0, 1)
        log["steps"][name] = {"model": version, "seconds": secs}
        steps[name] = data
        return data

    def done(name):  # always called on the caller's thread (Streamlit can't draw from worker threads)
        if on_step:
            on_step(name, steps[name], log["steps"][name]["seconds"])

    drive_path = f"/RedPen/Assessments/{module}/{assessment}/"
    files = {"brief.txt": brief, "rubric.txt": rubric, "clo-map.txt": clo_map}
    intake_in = f"Assessment folder: {drive_path}\n\n" + "\n\n".join(
        f"===== {n} ({drive_path}{n}) =====\n{t}" for n, t in files.items())
    if lecturer_email:
        intake_in += f"\n\nLecturer email: {lecturer_email}"

    t_start = time.time()
    intake = step("01-intake", instructions("01-intake.md"), intake_in)
    done("01-intake")
    if lecturer_email:
        intake["lecturer_email"] = lecturer_email
    intake_json = json.dumps(intake, ensure_ascii=False)

    with cf.ThreadPoolExecutor(3) as ex:
        futs = {ex.submit(step, f"02-{p}", instructions(f), intake_json): p for p, f in PERSONAS.items()}
        attempts = {}
        for fut in cf.as_completed(futs):
            attempts[futs[fut]] = fut.result()
            done(f"02-{futs[fut]}")
    attempts = {p: attempts[p] for p in PERSONAS}  # fixed order for the Examiner

    examiner = step("05-examiner", instructions("05-examiner.md"),
                    json.dumps({"intake": intake, **attempts}, ensure_ascii=False))
    done("05-examiner")

    verdict_sys = instructions("06-verdict.md")
    if model_label != "pro":
        verdict_sys = verdict_sys.replace('model: "pro"', f'model: "{model_label}"').replace(
            '"model": "pro"', f'"model": "{model_label}"')
    verdict = step("06-verdict", verdict_sys, json.dumps(
        {"intake": intake, "examiner": examiner, "run_date": run_date}, ensure_ascii=False))
    done("06-verdict")
    if lecturer_email:
        verdict["lecturer_email"] = lecturer_email

    log["total_seconds"] = round(time.time() - t_start, 1)
    errs, warns = check(verdict)
    log["contract"] = {"ok": not errs, "errors": errs, "warnings": warns}
    return {"verdict": verdict, "steps": steps, "log": log}


def demo_runs():
    """Names of saved runs in data/demo-runs/, e.g. ['BET150_A1', 'DSA201_A1', ...]."""
    return sorted(p.name for p in DEMO.iterdir() if (p / "06-verdict.json").exists()) if DEMO.exists() else []


def load_demo(name):
    """A saved run, same shape as run_audit() returns. No API calls."""
    d = DEMO / name
    steps = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("0*.json"))}
    log = json.loads((d / "run-log.json").read_text()) if (d / "run-log.json").exists() else {}
    return {"verdict": steps["06-verdict"], "steps": steps, "log": log}


def _save(result, out):
    out.mkdir(parents=True, exist_ok=True)
    for name, data in result["steps"].items():
        (out / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    (out / "run-log.json").write_text(json.dumps(result["log"], indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="+", help="assessment folders with brief.txt, rubric.txt, clo-map.txt")
    ap.add_argument("--out", default=str(ROOT / "data" / "dryrun"), help="where to save each run")
    ap.add_argument("--save-demo", action="store_true", help="also save to data/demo-runs/ (synthetic data only)")
    ap.add_argument("--email", help="lecturer email to put in the verdict")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--parallel", type=int, default=2)
    a = ap.parse_args()
    key = api_key()
    print("Models (in order): " + ", ".join(models()))

    def one(folder):
        folder = pathlib.Path(folder)
        module, assessment = folder.parent.name, folder.name
        txt = {n: (folder / n).read_text(encoding="utf-8") for n in ("brief.txt", "rubric.txt", "clo-map.txt")}
        res = run_audit(txt["brief.txt"], txt["rubric.txt"], txt["clo-map.txt"], module, assessment,
                        lecturer_email=a.email, run_date=a.date, key=key,
                        on_step=lambda n, d, s: print(f"  {module} {assessment} {n}: {s}s", flush=True))
        name = f"{module}_{assessment}"
        _save(res, pathlib.Path(a.out) / name)
        if a.save_demo:
            if "data/real" in str(folder.resolve()):
                raise AuditError("refusing to save real data to data/demo-runs/")
            _save(res, DEMO / name)
        return name, res

    failed = 0
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(one, f): f for f in a.folders}
        for fut in cf.as_completed(futs):
            try:
                name, res = fut.result()
                v, c = res["verdict"], res["log"]["contract"]
                print(f"DONE {name} exposure={v.get('exposure')} totals={v.get('persona_totals')} "
                      f"CLOs at risk={[x.get('id') for x in v.get('clos_at_risk', [])]} "
                      f"{res['log']['total_seconds']}s contract={'OK' if c['ok'] else 'FAIL'}")
                for m in c["errors"] + c["warnings"] + res["log"]["warnings"]:
                    print(f"     ! {m}")
            except Exception as e:  # keep going with other assessments
                failed += 1
                print(f"FAIL {futs[fut]}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
