"""RedPen multi-agent orchestrator, run from Google Antigravity.

The same Gemini agents as the RedPen app (prompts in ../agents/, schemas in ../agents/schemas/), orchestrated as a
small dependency graph and executed in waves:

    wave 1  Intake
    wave 2  Copy-paster | Prompt engineer | Honest helper      (in parallel)
    wave 3  Examiner
    wave 4  Verdict                                             (+ code guardrail: the exposure rule)
    wave 5  Redesign                                            (only if exposure is HIGH or MEDIUM)
    gate    Lecturer approval                                   (a human decides; nothing is sent from here)

Every agent's output is checked against its JSON schema. A rejected output goes back to the same agent with the
validation errors (self-correction, up to 2 retries). Each run is written to runs/<run-id>/: one JSON file per agent,
trace.json (prompt file + hash, model, seconds, attempts, schema result for every agent) and report.md (the
orchestration diagram with the real results).

Commands
    python orchestrator.py agents                          list the agents, their prompts and schemas
    python orchestrator.py audit <folder> [--module X]     run the pipeline on brief.txt / rubric.txt / clo-map.txt
    python orchestrator.py approve <run-dir> <R1|R2|R3>    the lecturer's decision: prepare the follow-up (no sending)
    python orchestrator.py compare <run-dir> [<saved-run>] compare with a saved RedPen run in ../data/demo-runs/

Swarm mode (each agent is an Antigravity swarm worker; see .agents/skills/redpen-swarm/SKILL.md)
    swarm-init <folder>            start a run;   prompt <run> <agent>  the agent's instructions
    input <run> <agent>            its exact input (refuses until its dependencies have submitted)
    submit <run> <agent> <file>    schema check (+ guardrail for the Verdict); prints the next agents
    status <run> / finish <run>    progress / write trace + report

Backends (picked automatically, or with --backend)
    gemini      Google Gemini API via the google-genai SDK (GEMINI_API_KEY in ../.env or antigravity/.env)
    openrouter  Gemini models through OpenRouter (OPENROUTER_API_KEY)
    replay      no API calls: replays a saved RedPen run from ../data/demo-runs/ (offline demo and tests;
                every file it writes says backend "replay")
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # google-auth / urllib3 nag about Python 3.9 and LibreSSL

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AGENTS_DIR = ROOT / "agents"
SCHEMAS = AGENTS_DIR / "schemas"
DEMO_RUNS = ROOT / "data" / "demo-runs"
POLICY = ROOT / "data" / "policy" / "assessment-design-guide.txt"
RUNS = HERE / "runs"

GEMINI_MODELS = os.environ.get("AG_MODELS", "gemini-3-flash-preview,gemini-flash-latest,gemini-2.5-flash").split(",")
OPENROUTER_MODELS = os.environ.get(
    "AG_OPENROUTER_MODELS", "google/gemini-3-flash-preview,google/gemini-2.5-flash").split(",")
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 2


class OrchestratorError(Exception):
    pass


# --------------------------------------------------------------------------------------------------------------------
# The agents. One row per agent: what it reads, which prompt and schema it uses, and what it depends on.
# --------------------------------------------------------------------------------------------------------------------
AGENTS = [
    {"id": "01-intake", "name": "Intake", "prompt": "audit/01-intake.md", "schema": "01-intake.schema.json",
     "needs": [], "job": "Reads the brief, rubric and CLO map; lists the tasks, criteria, marks and pass mark."},
    {"id": "02-copy_paster", "name": "Copy-paster", "prompt": "audit/02-persona-copy-paster.md",
     "schema": "02-persona.schema.json", "needs": ["01-intake"],
     "job": "AI student 1: pastes the brief into a chatbot and submits the answer unedited."},
    {"id": "02-prompt_engineer", "name": "Prompt engineer", "prompt": "audit/03-persona-prompt-engineer.md",
     "schema": "02-persona.schema.json", "needs": ["01-intake"],
     "job": "AI student 2: plans, drafts and self-critiques with AI, task by task."},
    {"id": "02-honest_helper", "name": "Honest helper", "prompt": "audit/04-persona-honest-helper.md",
     "schema": "02-persona.schema.json", "needs": ["01-intake"],
     "job": "AI student 3: uses AI only the way the brief allows."},
    {"id": "05-examiner", "name": "Examiner", "prompt": "audit/05-examiner.md", "schema": "05-examiner.schema.json",
     "needs": ["01-intake", "02-copy_paster", "02-prompt_engineer", "02-honest_helper"],
     "job": "Marks all three attempts on the real rubric, like a lecturer with no AI detector."},
    {"id": "06-verdict", "name": "Verdict", "prompt": "audit/06-verdict.md", "schema": "06-verdict.schema.json",
     "needs": ["01-intake", "05-examiner"],
     "job": "Turns the marks into HIGH / MEDIUM / LOW AI-exposure and the CLOs no longer reliably evidenced."},
    {"id": "07-redesign", "name": "Redesign", "prompt": "fix/01-redesign.md", "schema": "07-redesign.schema.json",
     "needs": ["06-verdict"], "when": "exposure is HIGH or MEDIUM",
     "job": "Proposes 2-3 redesigns that still test the same CLOs, each with an AI Assessment Scale level."},
]
BY_ID = {a["id"]: a for a in AGENTS}
PERSONAS = ["copy_paster", "prompt_engineer", "honest_helper"]


def prompt_of(agent):
    """The agent's instructions: the first ``` block under '## Instructions' in its prompt file (as the app does)."""
    text = (AGENTS_DIR / agent["prompt"]).read_text(encoding="utf-8")
    m = re.search(r"^## Instructions.*?^```[a-z]*\n(.*?)^```", text, re.S | re.M)
    if not m:
        raise OrchestratorError(f"no '## Instructions' block in agents/{agent['prompt']}")
    return m.group(1).strip()


def schema_errors(agent, data):
    import jsonschema
    schema = json.loads((SCHEMAS / agent["schema"]).read_text(encoding="utf-8"))
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"[:300]
            for e in sorted(validator.iter_errors(data), key=str)][:8]


def expected_exposure(totals, pass_mark):
    """The exposure rule from agents/audit/06-verdict.md, enforced in code (the model is not trusted with it)."""
    if (totals.get("copy_paster") or 0) >= pass_mark:
        return "HIGH"
    if (totals.get("prompt_engineer") or 0) >= pass_mark:
        return "MEDIUM"
    return "LOW"


# --------------------------------------------------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------------------------------------------------
def load_env():
    for f in (ROOT / ".env", HERE / ".env"):
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
                if m and m.group(2) and not os.environ.get(m.group(1)):
                    os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")


class GeminiBackend:
    name = "gemini"

    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.models = [m.strip() for m in GEMINI_MODELS if m.strip()]

    def call(self, agent, system, user, attempt):
        from google.genai import types
        last = None
        for model in self.models[attempt % len(self.models):] + self.models[:attempt % len(self.models)]:
            try:
                r = self.client.models.generate_content(
                    model=model, contents=user,
                    config=types.GenerateContentConfig(system_instruction=system,
                                                       response_mime_type="application/json"))
                return r.text or "", getattr(r, "model_version", None) or model
            except Exception as e:  # quota, overload, unknown model: try the next model
                last = f"{model}: {str(e)[:200]}"
        raise OrchestratorError(f"{agent['name']}: every Gemini model failed ({last})")


class OpenRouterBackend:
    name = "openrouter"

    def __init__(self):
        self.key = os.environ["OPENROUTER_API_KEY"]
        self.models = [m.strip() for m in OPENROUTER_MODELS if m.strip()]
        if not os.environ.get("AG_OPENROUTER_MODELS"):
            # Same Gemini models, in the same order, as the RedPen app's audit engine (proven live; respects
            # REDPEN_MODELS and its Gemini-only guard), so the Agents page and the Audit page behave alike.
            try:
                sys.path.insert(0, str(ROOT / "tools"))
                import redpen_audit
                self.models = [m for m in redpen_audit.models() if m.startswith("google/")] or self.models
            except Exception:
                pass

    def call(self, agent, system, user, attempt):
        last = None
        for model in self.models[attempt % len(self.models):] + self.models[:attempt % len(self.models)]:
            body = json.dumps({"model": model, "response_format": {"type": "json_object"},
                               "messages": [{"role": "system", "content": system},
                                            {"role": "user", "content": user}]}).encode()
            req = urllib.request.Request(OPENROUTER_API, data=body, method="POST", headers={
                "Content-Type": "application/json", "Authorization": f"Bearer {self.key}", "X-Title": "RedPen"})
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    d = json.load(r)
                if "error" in d:
                    raise OrchestratorError(str(d["error"])[:200])
                return d["choices"][0]["message"]["content"] or "", d.get("model", model)
            except Exception as e:  # HTTP error, timeout (socket.timeout on 3.9), bad JSON, empty choices: next model
                last = f"{model}: {type(e).__name__}: {str(e)[:200]}"
        raise OrchestratorError(f"{agent['name']}: every OpenRouter model failed ({last})")


class ReplayBackend:
    """No API calls: returns the outputs of a saved RedPen run, so the orchestration can be shown and tested offline."""
    name = "replay"

    def __init__(self, saved_run, speed=None):
        """speed: replay each agent at its real recorded duration divided by speed (None = 0.2 s each)."""
        self.dir = DEMO_RUNS / saved_run
        if not self.dir.is_dir():
            raise OrchestratorError(f"no saved run {saved_run} in data/demo-runs/")
        self.speed = speed
        log = self.dir / "run-log.json"
        self.recorded = json.loads(log.read_text(encoding="utf-8")).get("steps", {}) if log.exists() else {}

    def call(self, agent, system, user, attempt):
        f = self.dir / f"{agent['id']}.json"
        if not f.exists():
            raise OrchestratorError(f"saved run {self.dir.name} has no {f.name}")
        secs = self.recorded.get(agent["id"], {}).get("seconds", 8.0)
        time.sleep(min(secs / self.speed, 8.0) if self.speed else 0.2)
        return f.read_text(encoding="utf-8"), f"replay:{self.dir.name}"


def pick_backend(choice, replay_run):
    load_env()
    if choice == "replay" or (choice == "auto" and replay_run):
        return ReplayBackend(replay_run or "CCP_A1")
    if choice in ("auto", "gemini") and os.environ.get("GEMINI_API_KEY"):
        return GeminiBackend()
    if choice in ("auto", "openrouter") and os.environ.get("OPENROUTER_API_KEY"):
        return OpenRouterBackend()
    raise OrchestratorError("no API key: add GEMINI_API_KEY=... to redPen/.env (free key: aistudio.google.com), "
                            "or run with --backend replay to replay a saved run offline")


# --------------------------------------------------------------------------------------------------------------------
# The orchestrator
# --------------------------------------------------------------------------------------------------------------------
def parse_json(text):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    try:
        return json.loads(t, strict=False)
    except json.JSONDecodeError:
        obj, _ = json.JSONDecoder(strict=False).raw_decode(t[t.find("{"):]) if "{" in t else (None, 0)
        if obj is None:
            raise
        return obj


class Orchestrator:
    def __init__(self, backend, module, assessment, files, out_dir, log=print, on_event=None, label=None):
        """on_event(kind, agent_id, info) is called on the caller's thread: kind is "start", "done", "guardrail"
        or "skip" (for live views such as the app's Agents page)."""
        self.backend, self.module, self.assessment, self.files = backend, module, assessment, files
        self.out, self.log, self.on_event, self.label = out_dir, log, on_event or (lambda *a: None), label
        self.results, self.trace = {}, {"run_id": out_dir.name, "module": module, "assessment": assessment,
                                         "backend": backend.name, "started": dt.datetime.now().isoformat(timespec="seconds"),
                                         "agents": {}, "waves": [], "guardrails": [], "skipped": {}}

    # What each agent receives. Same inputs as the RedPen app (tools/redpen_audit.py, tools/redpen_fix.py).
    def inputs_for(self, agent_id):
        r = self.results
        if agent_id == "01-intake":
            path = f"/RedPen/Assessments/{self.module}/{self.assessment}/"
            return f"Assessment folder: {path}\n\n" + "\n\n".join(
                f"===== {n} ({path}{n}) =====\n{t}" for n, t in self.files.items())
        if agent_id.startswith("02-"):
            return json.dumps(r["01-intake"], ensure_ascii=False)
        if agent_id == "05-examiner":
            return json.dumps({"intake": r["01-intake"], **{p: r[f"02-{p}"] for p in PERSONAS}}, ensure_ascii=False)
        if agent_id == "06-verdict":
            return json.dumps({"intake": r["01-intake"], "examiner": r["05-examiner"],
                               "run_date": dt.date.today().isoformat()}, ensure_ascii=False)
        if agent_id == "07-redesign":
            return json.dumps({"verdict": r["06-verdict"], "original_brief": self.files["brief.txt"],
                               "assessment_design_guide": POLICY.read_text(encoding="utf-8")}, ensure_ascii=False)
        raise OrchestratorError(agent_id)

    def system_for(self, agent):
        system = prompt_of(agent)
        if agent["id"] == "06-verdict":
            label = self.label or ("flash" if "flash" in ",".join(getattr(self.backend, "models", ["flash"])) else "pro")
            system = system.replace('model: "pro"', f'model: "{label}"').replace('"model": "pro"', f'"model": "{label}"')
        return system

    def run_agent(self, agent_id):
        agent = BY_ID[agent_id]
        system, user = self.system_for(agent), self.inputs_for(agent_id)
        t0, attempts, feedback, problems, model = time.time(), 0, "", [], None
        data = None
        for attempt in range(MAX_RETRIES + 1):
            attempts += 1
            text, model = self.backend.call(agent, system, user + feedback, attempt)
            try:
                data = parse_json(text)
                problems = schema_errors(agent, data)
            except (json.JSONDecodeError, ValueError) as e:
                data, problems = None, [f"not valid JSON: {str(e)[:150]}"]
            if not problems:
                break
            # Self-correction: hand the agent its own validation errors and ask again.
            feedback = ("\n\n----- YOUR PREVIOUS ANSWER WAS REJECTED -----\n" + "\n".join(problems) +
                        "\nReturn ONLY the corrected JSON object, matching the required format exactly.")
        if data is None:
            raise OrchestratorError(f"{agent['name']}: no valid JSON after {attempts} attempts: {problems}")
        self.trace["agents"][agent_id] = {
            "name": agent["name"], "prompt_file": f"agents/{agent['prompt']}",
            "prompt_sha256": hashlib.sha256(system.encode()).hexdigest()[:12], "schema": f"agents/schemas/{agent['schema']}",
            "model": model, "seconds": round(time.time() - t0, 1), "attempts": attempts,
            "schema_ok": not problems, "schema_errors": problems, "input_chars": len(user)}
        return data

    def guard_verdict(self):
        v = self.results["06-verdict"]
        try:
            want = expected_exposure(v.get("persona_totals", {}), float(v.get("pass_mark", 50)))
        except (TypeError, ValueError):
            return
        if v.get("exposure") != want:
            self.trace["guardrails"].append(f"Verdict said {v.get('exposure')}; the exposure rule gives {want}: corrected")
            v["exposure"] = want
            if want == "LOW":
                v["clos_at_risk"] = []
        else:
            self.trace["guardrails"].append(f"Exposure rule check passed ({want})")

    def ready(self, done):
        out = []
        for a in AGENTS:
            if a["id"] in done or a["id"] in self.trace["skipped"] or not all(n in done for n in a["needs"]):
                continue
            if a.get("when") and self.results.get("06-verdict", {}).get("exposure") not in ("HIGH", "MEDIUM"):
                self.trace["skipped"][a["id"]] = f"condition not met: {a['when']}"
                continue
            out.append(a["id"])
        return out

    def run(self):
        t_start, done, wave = time.time(), set(), 0
        while True:
            batch = self.ready(done)
            if not batch:
                break
            wave += 1
            names = " | ".join(BY_ID[i]["name"] for i in batch)
            self.log(f"wave {wave}: {names}" + ("   (in parallel)" if len(batch) > 1 else ""))
            for i in batch:
                self.on_event("start", i, {"wave": wave})
            with cf.ThreadPoolExecutor(len(batch)) as ex:
                futs = {ex.submit(self.run_agent, i): i for i in batch}
                for fut in cf.as_completed(futs):
                    i = futs[fut]
                    self.results[i] = fut.result()
                    t = self.trace["agents"][i]
                    self.log(f"   ✓ {t['name']:<16} {t['seconds']:>5}s  attempts {t['attempts']}  "
                             f"schema {'ok' if t['schema_ok'] else 'FAILED'}")
                    self.save(i)
                    self.on_event("done", i, t)
            self.trace["waves"].append(batch)
            done.update(batch)
            if "06-verdict" in batch:
                self.guard_verdict()
                self.save("06-verdict")
                self.log(f"   guardrail: {self.trace['guardrails'][-1]}")
                self.on_event("guardrail", "06-verdict", {"text": self.trace["guardrails"][-1],
                                                          "exposure": self.results["06-verdict"].get("exposure")})
        for i, why in self.trace["skipped"].items():
            self.log(f"skipped: {BY_ID[i]['name']} ({why})")
            self.on_event("skip", i, {"why": why})
        self.trace["total_seconds"] = round(time.time() - t_start, 1)
        v = self.results.get("06-verdict", {})
        self.trace["approval"] = {"status": "waiting for the lecturer" if "07-redesign" in self.results
                                  else "not needed (LOW exposure)", "decision": None}
        self.write_trace()
        write_report(self.out)
        return v

    def save(self, agent_id):
        (self.out / f"{agent_id}.json").write_text(json.dumps(self.results[agent_id], indent=2, ensure_ascii=False),
                                                   encoding="utf-8")

    def write_trace(self):
        (self.out / "trace.json").write_text(json.dumps(self.trace, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------------------------------------------------
# Report: the orchestration diagram filled in with the real results of this run
# --------------------------------------------------------------------------------------------------------------------
def rel(path):
    """Path relative to this folder when it is inside it (for commands you can copy), else absolute."""
    try:
        return Path(path).resolve().relative_to(HERE)
    except ValueError:
        return Path(path).resolve()


def _load(run_dir, name):
    f = run_dir / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def write_report(run_dir):
    tr = _load(run_dir, "trace.json")
    v = _load(run_dir, "06-verdict.json") or {}
    red = _load(run_dir, "07-redesign.json")
    ag = tr["agents"]
    tot, grades = v.get("persona_totals", {}), v.get("persona_grades", {})

    def node(i, extra=""):
        a = ag.get(i)
        return f'{BY_ID[i]["name"]}<br/>{a["seconds"]}s{extra}' if a else BY_ID[i]["name"]

    p = {x: f"<br/>{grades.get(x, '?')} {tot.get(x, '?')}%" for x in PERSONAS}
    exposure = v.get("exposure", "?")
    approval = tr.get("approval", {})
    gate = (f"Approved {approval['decision']}" if approval.get("decision") else approval.get("status", ""))
    redesign_node = (f'R["{node("07-redesign")}<br/>{len(red.get("options", []))} options"]' if red
                     else 'R["Redesign<br/>skipped"]')
    mermaid = "\n".join([
        "flowchart LR",
        f'  IN[/"brief + rubric + CLO map"/] --> I["{node("01-intake")}"]',
        f'  I --> P1["{node("02-copy_paster", p["copy_paster"])}"]',
        f'  I --> P2["{node("02-prompt_engineer", p["prompt_engineer"])}"]',
        f'  I --> P3["{node("02-honest_helper", p["honest_helper"])}"]',
        f'  P1 & P2 & P3 --> E["{node("05-examiner")}"]',
        f'  E --> V["{node("06-verdict")}<br/><b>{exposure}</b>"]',
        '  V --> G{"guardrail:<br/>exposure rule"}',
        '  G --> C{"HIGH or<br/>MEDIUM?"}',
        f'  C -- yes --> {redesign_node}',
        f'  R --> H(["Lecturer approval<br/>{gate}"])',
        '  C -- no --> REG[("register")]',
        '  H --> OUT[["Jira card · Gmail report · Calendar invite · revised brief"]]',
    ])
    rows = "\n".join(
        f"| {w} | {a['name']} | `{a['prompt_file']}` | `{a['model']}` | {a['seconds']} | {a['attempts']} | "
        f"{'✓' if a['schema_ok'] else '✗ ' + '; '.join(a['schema_errors'])[:80]} |"
        for w, batch in enumerate(tr["waves"], 1) for a in (ag[i] for i in batch))
    clos = "\n".join(f"- **{c.get('id')}** {c.get('text', '')}: {c.get('why', '')}" for c in v.get("clos_at_risk", [])) \
        or "- none: every learning outcome is still evidenced"
    opts = ""
    if red:
        decided = approval.get("decision")
        opts = ("\n## Redesign options" + ("" if decided else " (waiting for the lecturer)") + "\n\n" + "\n".join(
            f"- **{o.get('id')} · {o.get('title')}** (AIAS level {o.get('aias_level')}, {o.get('lane')} lane)"
            + (" **recommended**" if o.get("id") == red.get("recommended") else "")
            + (" ✅ **approved by the lecturer**" if o.get("id") == decided else "")
            for o in red.get("options", [])))
        if decided:
            opts += (f"\n\n**Lecturer approved {decided}** at {approval.get('at')}. Prepared in `outbox/` (not sent): "
                     + ", ".join(approval.get("prepared", [])) + "\n")
        else:
            opts += (f"\n\nTo approve: `python orchestrator.py approve {rel(run_dir)} "
                     f"{red.get('recommended', 'R1')}`\n")
    md = f"""# RedPen run {tr['run_id']}

**{tr['module']} {tr['assessment']}** · backend `{tr['backend']}` · {tr['started']} · {tr.get('total_seconds', '?')} s in total

## Verdict: {exposure} AI-exposure

{v.get('summary', '')}

| AI student | Grade | Total | Pass mark |
|---|---|---|---|
""" + "\n".join(f"| {BY_ID['02-' + x]['name']} | {grades.get(x, '?')} | {tot.get(x, '?')}% | {v.get('pass_mark', '?')}% |"
                for x in PERSONAS) + f"""

**Learning outcomes no longer reliably evidenced**

{clos}

## How the agents ran

```mermaid
{mermaid}
```

| Wave | Agent | Prompt | Model | Seconds | Attempts | Output schema |
|---|---|---|---|---|---|---|
{rows}

**Guardrails:** {'; '.join(tr['guardrails']) or 'none'}
{('**Skipped:** ' + '; '.join(f"{BY_ID[i]['name']} ({w})" for i, w in tr['skipped'].items())) if tr['skipped'] else ''}
{opts}"""
    (run_dir / "report.md").write_text(md, encoding="utf-8")


# --------------------------------------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------------------------------------
def cmd_agents(_):
    print(f"{'Agent':<17}{'Depends on':<34}{'Prompt':<46}Schema")
    for a in AGENTS:
        deps = ", ".join(BY_ID[n]["name"] for n in a["needs"]) or "(lecturer's files)"
        print(f"{a['name']:<17}{deps[:32]:<34}{'agents/' + a['prompt']:<46}{a['schema']}")
        print(f"{'':<17}{a['job']}" + (f"  [runs only if {a['when']}]" if a.get("when") else ""))
    print("\nThen: lecturer approval (human) -> Jira card, Gmail report, Calendar invite, revised brief.")


def read_folder(folder):
    folder = Path(folder)
    files = {}
    for name, required in (("brief.txt", True), ("rubric.txt", False), ("clo-map.txt", False)):
        f = folder / name
        if f.exists():
            files[name] = f.read_text(encoding="utf-8")
        elif required:
            raise OrchestratorError(f"{folder} has no brief.txt")
    files.setdefault("rubric.txt", "(no separate rubric file was given: the marking scheme is inside the brief)")
    files.setdefault("clo-map.txt", "(no CLO map was given: take the CLOs from the brief and the rubric)")
    return files


def cmd_audit(a):
    folder = Path(a.folder).resolve()
    module = (a.module or folder.parent.name).upper()
    assessment = (a.assessment or folder.name).upper()
    backend = pick_backend(a.backend, a.replay)
    run_id = f"{module}_{assessment}_{backend.name}_{dt.datetime.now():%Y%m%d-%H%M%S}"
    out = RUNS / run_id
    out.mkdir(parents=True, exist_ok=True)
    print(f"RedPen orchestrator · {module} {assessment} · backend {backend.name} · {len(AGENTS)} agents\n")
    v = Orchestrator(backend, module, assessment, read_folder(folder), out).run()
    print(f"\nVERDICT: {v.get('exposure')} AI-exposure · CLOs at risk: "
          f"{', '.join(c.get('id', '?') for c in v.get('clos_at_risk', [])) or 'none'}")
    print(f"Report: {rel(out)}/report.md")
    if (out / "07-redesign.json").exists():
        print("Waiting for the lecturer: approve with "
              f"`python orchestrator.py approve {rel(out)} R1` (nothing is sent until then)")


def cmd_approve(a):
    run_dir = Path(a.run_dir)
    run_dir = run_dir if run_dir.is_absolute() else (HERE / run_dir)
    v, red, tr = _load(run_dir, "06-verdict.json"), _load(run_dir, "07-redesign.json"), _load(run_dir, "trace.json")
    if not red:
        raise OrchestratorError("this run has no redesign (LOW exposure): nothing to approve")
    opt = next((o for o in red.get("options", []) if o.get("id") == a.option.upper()), None)
    if not opt:
        raise OrchestratorError(f"no option {a.option} (have: {', '.join(o.get('id') for o in red.get('options', []))})")
    sys.path.insert(0, str(ROOT / "tools"))
    import redpen_fix as rf  # the app's own follow-up builders: same email, invite and Jira card text
    out = run_dir / "outbox"
    out.mkdir(exist_ok=True)
    brief = read_folder_from_trace(run_dir)
    (out / "email.txt").write_text(f"Subject: {rf.email_subject(v)}\n\n{rf.email_body(v, red, opt)}", encoding="utf-8")
    (out / f"{v.get('module')}_{v.get('assessment')}_revised.txt").write_text(rf.revised_brief(brief, v, opt),
                                                                             encoding="utf-8")
    (out / "jira-card.json").write_text(json.dumps({"summary": f"{v.get('module')} {v.get('assessment')}: "
                                                    f"{v.get('exposure')} AI-exposure", "labels": rf.jira_labels(v),
                                                    "description": rf.jira_description(v, opt)}, indent=2),
                                        encoding="utf-8")
    if v.get("exposure") == "HIGH":
        (out / "review.ics").write_text(rf.ics_invite(v), encoding="utf-8")
    tr["approval"] = {"status": "approved", "decision": opt.get("id"), "title": opt.get("title"),
                      "at": dt.datetime.now().isoformat(timespec="seconds"),
                      "prepared": sorted(p.name for p in out.iterdir())}
    (run_dir / "trace.json").write_text(json.dumps(tr, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(run_dir)
    print(f"Approved {opt.get('id')}: {opt.get('title')}")
    print(f"Prepared in {rel(out)}/: " + ", ".join(tr["approval"]["prepared"]))
    print("Nothing was sent. The RedPen app sends these for real (Jira, Gmail, Calendar) when a lecturer approves there.")


def read_folder_from_trace(run_dir):
    intake = _load(run_dir, "01-intake.json") or {}
    sys.path.insert(0, str(ROOT / "tools"))
    import redpen_fix as rf
    return rf.brief_from_intake(intake)


def cmd_compare(a):
    run_dir = Path(a.run_dir)
    run_dir = run_dir if run_dir.is_absolute() else (HERE / run_dir)
    mine = _load(run_dir, "06-verdict.json")
    saved_name = a.saved or f"{mine.get('module', '')}_{mine.get('assessment', '')}".replace("-3-2", "")
    candidates = [saved_name, "CCP_A1" if mine.get("module", "").startswith("CT074") else saved_name]
    saved_dir = next((DEMO_RUNS / c for c in candidates if (DEMO_RUNS / c / "06-verdict.json").exists()), None)
    if not saved_dir:
        raise OrchestratorError(f"no saved run to compare with; pass one of: {', '.join(sorted(p.name for p in DEMO_RUNS.iterdir() if p.is_dir()))}")
    theirs = _load(saved_dir, "06-verdict.json")
    levels = ["LOW", "MEDIUM", "HIGH"]
    gap = abs(levels.index(mine.get("exposure", "LOW")) - levels.index(theirs.get("exposure", "LOW")))
    print(f"Antigravity run: {run_dir.name}\nSaved RedPen run: data/demo-runs/{saved_dir.name}\n")
    print(f"{'':<22}{'Antigravity':<14}{'RedPen app':<14}Difference")
    print(f"{'Exposure':<22}{mine.get('exposure'):<14}{theirs.get('exposure'):<14}"
          f"{'same' if gap == 0 else f'{gap} level(s)'}")
    for x in PERSONAS:
        m_, t_ = mine.get("persona_totals", {}).get(x), theirs.get("persona_totals", {}).get(x)
        d = f"{m_ - t_:+}" if isinstance(m_, (int, float)) and isinstance(t_, (int, float)) else "?"
        print(f"{BY_ID['02-' + x]['name'] + ' %':<22}{str(m_):<14}{str(t_):<14}{d}")
    mc = sorted(c.get("id") for c in mine.get("clos_at_risk", []))
    tc = sorted(c.get("id") for c in theirs.get("clos_at_risk", []))
    print(f"{'CLOs at risk':<22}{','.join(mc) or '-':<14}{','.join(tc) or '-':<14}{'same' if mc == tc else 'differs'}")
    print("\nResult: " + ("MATCH (same exposure level)" if gap == 0 else
                         "CLOSE (one level apart: single runs can move one level)" if gap == 1 else "DIFFERENT"))


# --------------------------------------------------------------------------------------------------------------------
# Swarm mode: each agent is an Antigravity swarm worker. The workers fetch their prompt and their exact input here and
# hand their output back through `submit`, so they pass the same schema checks and guardrail as the Python run.
# --------------------------------------------------------------------------------------------------------------------
ALIASES = {a["name"].lower().replace(" ", "-"): a["id"] for a in AGENTS}
ALIASES.update({a["id"]: a["id"] for a in AGENTS})
ALIASES.update({a["id"].split("-", 1)[1].replace("_", "-"): a["id"] for a in AGENTS})


def agent_id_of(name):
    i = ALIASES.get(name.strip().lower())
    if not i:
        raise OrchestratorError(f"unknown agent {name!r}; use one of: {', '.join(sorted(set(ALIASES) - set(BY_ID)))}")
    return i


class SwarmBackend:
    name = "antigravity-swarm"
    models = []


def run_path(run_dir):
    p = Path(run_dir)
    p = p if p.is_absolute() else (HERE / p)
    if not (p / "trace.json").exists():
        raise OrchestratorError(f"{run_dir} is not a run folder (no trace.json)")
    return p


def load_swarm(run_dir):
    """Rebuild an Orchestrator from a swarm run folder (inputs/ + the agents' submitted outputs)."""
    p = run_path(run_dir)
    tr = _load(p, "trace.json")
    files = {n: (p / "inputs" / n).read_text(encoding="utf-8") for n in ("brief.txt", "rubric.txt", "clo-map.txt")}
    orch = Orchestrator(SwarmBackend(), tr["module"], tr["assessment"], files, p, log=lambda *_: None,
                        label=tr.get("label"))
    orch.trace = tr
    for a in AGENTS:
        f = p / f"{a['id']}.json"
        if f.exists():
            orch.results[a["id"]] = json.loads(f.read_text(encoding="utf-8"))
    return orch


def levels():
    lv = {}
    for a in AGENTS:  # AGENTS is in dependency order
        lv[a["id"]] = 1 + max((lv[n] for n in a["needs"]), default=0)
    return lv


def next_agents(orch):
    done = set(orch.results)
    out = []
    for a in AGENTS:
        if a["id"] in done or not all(n in done for n in a["needs"]):
            continue
        if a.get("when") and orch.results.get("06-verdict", {}).get("exposure") not in ("HIGH", "MEDIUM"):
            continue
        out.append(a["id"])
    return out


def cmd_swarm_init(a):
    folder = Path(a.folder).resolve()
    module = (a.module or folder.parent.name).upper()
    assessment = (a.assessment or folder.name).upper()
    run_id = f"{module}_{assessment}_swarm_{dt.datetime.now():%Y%m%d-%H%M%S}"
    out = RUNS / run_id
    (out / "inputs").mkdir(parents=True, exist_ok=True)
    (out / "drafts").mkdir(exist_ok=True)
    for n, t in read_folder(folder).items():
        (out / "inputs" / n).write_text(t, encoding="utf-8")
    trace = {"run_id": run_id, "module": module, "assessment": assessment, "backend": "antigravity-swarm",
             "label": a.label, "source": str(folder), "started": dt.datetime.now().isoformat(timespec="seconds"),
             "agents": {}, "waves": [], "guardrails": [], "skipped": {}, "events": []}
    (out / "trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(f"RUN={rel(out)}")
    print(f"{module} {assessment}: swarm run ready. First agent: intake.")


def _event(orch, text):
    orch.trace.setdefault("events", []).append({"t": dt.datetime.now().isoformat(timespec="seconds"), "e": text})


def cmd_prompt(a):
    orch = load_swarm(a.run_dir)
    print(orch.system_for(BY_ID[agent_id_of(a.agent)]))


def cmd_input(a):
    orch = load_swarm(a.run_dir)
    i = agent_id_of(a.agent)
    missing = [BY_ID[n]["name"] for n in BY_ID[i]["needs"] if n not in orch.results]
    if missing:
        raise OrchestratorError(f"{BY_ID[i]['name']} must wait for: {', '.join(missing)}")
    orch.trace.setdefault("started_at", {}).setdefault(i, time.time())
    _event(orch, f"{BY_ID[i]['name']} started")
    orch.write_trace()
    print(orch.inputs_for(i))


def cmd_submit(a):
    orch = load_swarm(a.run_dir)
    i = agent_id_of(a.agent)
    agent = BY_ID[i]
    f = Path(a.file)
    f = f if f.is_absolute() else Path.cwd() / f
    tries = orch.trace.setdefault("tries", {})
    tries[i] = tries.get(i, 0) + 1
    try:
        data = parse_json(f.read_text(encoding="utf-8"))
        problems = schema_errors(agent, data)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        data, problems = None, [f"could not read JSON from {a.file}: {str(e)[:150]}"]
    if problems:
        _event(orch, f"{agent['name']} output rejected (attempt {tries[i]})")
        orch.write_trace()
        print(f"REJECTED ({agent['name']}, attempt {tries[i]}). Fix these and submit again:")
        print("\n".join(f"- {x}" for x in problems))
        sys.exit(2)
    orch.results[i] = data
    started = orch.trace.get("started_at", {}).get(i, time.time())
    orch.trace["agents"][i] = {
        "name": agent["name"], "prompt_file": f"agents/{agent['prompt']}",
        "prompt_sha256": hashlib.sha256(orch.system_for(agent).encode()).hexdigest()[:12],
        "schema": f"agents/schemas/{agent['schema']}", "model": "antigravity-swarm worker",
        "seconds": round(time.time() - started, 1), "attempts": tries[i], "schema_ok": True, "schema_errors": [],
        "input_chars": len(orch.inputs_for(i))}
    orch.save(i)
    msg = f"ACCEPTED: {agent['name']} output saved ({i}.json, attempt {tries[i]})."
    if i == "06-verdict":
        orch.guard_verdict()
        orch.save(i)
        msg += f" Guardrail: {orch.trace['guardrails'][-1]}."
        v = orch.results[i]
        msg += f" Verdict {v.get('exposure')}, CLOs at risk: {', '.join(c.get('id', '?') for c in v.get('clos_at_risk', [])) or 'none'}."
        if v.get("exposure") not in ("HIGH", "MEDIUM"):
            orch.trace["skipped"]["07-redesign"] = "condition not met: exposure is HIGH or MEDIUM"
    if i.startswith("02-"):
        msg += " Persona answers saved."
    _event(orch, f"{agent['name']} accepted")
    orch.write_trace()
    nxt = next_agents(orch)
    print(msg)
    print("NEXT: " + (", ".join(BY_ID[n]["name"] for n in nxt) if nxt else
                      "nothing: run is complete, tell the coordinator" if len(orch.results) >= 6 else
                      "waiting for the other agents of this wave"))


def cmd_status(a):
    orch = load_swarm(a.run_dir)
    for x in AGENTS:
        st = ("done" if x["id"] in orch.results else "skipped" if x["id"] in orch.trace.get("skipped", {})
              else "ready" if x["id"] in next_agents(orch) else "waiting")
        print(f"{x['name']:<17}{st}")


def cmd_finish(a):
    orch = load_swarm(a.run_dir)
    if "06-verdict" not in orch.results:
        raise OrchestratorError("the Verdict agent has not submitted yet")
    lv = levels()
    waves = {}
    for i in orch.results:
        waves.setdefault(lv[i], []).append(i)
    orch.trace["waves"] = [sorted(waves[k], key=list(BY_ID).index) for k in sorted(waves)]
    st = orch.trace.get("started_at", {})
    if st:
        orch.trace["total_seconds"] = round(time.time() - min(st.values()), 1)
    if "approval" not in orch.trace or not orch.trace["approval"].get("decision"):
        orch.trace["approval"] = {"status": "waiting for the lecturer" if "07-redesign" in orch.results
                                  else "not needed (LOW exposure)", "decision": None}
    orch.write_trace()
    write_report(orch.out)
    print(f"Report: {rel(orch.out)}/report.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description="RedPen multi-agent orchestrator (Gemini)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("agents")
    au = sub.add_parser("audit")
    au.add_argument("folder")
    au.add_argument("--module")
    au.add_argument("--assessment")
    au.add_argument("--backend", default="auto", choices=["auto", "gemini", "openrouter", "replay"])
    au.add_argument("--replay", help="saved run in data/demo-runs/ to replay (implies --backend replay)")
    apv = sub.add_parser("approve")
    apv.add_argument("run_dir")
    apv.add_argument("option")
    co = sub.add_parser("compare")
    co.add_argument("run_dir")
    co.add_argument("saved", nargs="?")
    si = sub.add_parser("swarm-init", help="start a run whose agents are Antigravity swarm workers")
    si.add_argument("folder")
    si.add_argument("--module")
    si.add_argument("--assessment")
    si.add_argument("--label", default="pro", choices=["flash", "pro"], help="model label written in the verdict")
    for name in ("prompt", "input"):
        x = sub.add_parser(name)
        x.add_argument("run_dir")
        x.add_argument("agent")
    sm = sub.add_parser("submit")
    sm.add_argument("run_dir")
    sm.add_argument("agent")
    sm.add_argument("file")
    for name in ("status", "finish"):
        sub.add_parser(name).add_argument("run_dir")
    a = ap.parse_args(argv)
    try:
        {"agents": cmd_agents, "audit": cmd_audit, "approve": cmd_approve, "compare": cmd_compare,
         "swarm-init": cmd_swarm_init, "prompt": cmd_prompt, "input": cmd_input, "submit": cmd_submit,
         "status": cmd_status, "finish": cmd_finish}[a.cmd](a)
    except OrchestratorError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
