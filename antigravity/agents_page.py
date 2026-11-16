"""The app's "Agents" page: RedPen's agent orchestration, live.

Draws the agent graph and updates it as each Gemini agent starts and finishes (waves, parallel fan-out, schema checks,
self-correction retries, the exposure-rule guardrail, the conditional Redesign and the lecturer approval gate), then
shows every agent's exact prompt next to its exact output.

Two modes: replay a saved audit (no API calls, open to everyone, labelled as a replay) or run live on Gemini (judge
access, uses the app's API key). Imported by ../streamlit_app.py; the engine is orchestrator.py in this folder.
"""
import datetime as dt
import html
import json
import tempfile
import time
from pathlib import Path

import streamlit as st

import orchestrator as o

LIVE_FOLDERS = {  # real APU briefs first, then the synthetic samples
    "CT074-3-2 A1 · Concurrent Programming (real APU brief)": ("pilot-real/CCP/A1", "CT074-3-2", "A1"),
    "DSTR LW1 · Data Structures (real APU brief)": ("pilot-real/DSTR/LW1", "DSTR", "LW1"),
    "DSTR LW2 · Data Structures (real APU brief)": ("pilot-real/DSTR/LW2", "DSTR", "LW2"),
    "CT050-3-2-WAPP GA · Web Applications (real APU brief)": ("pilot-real/WAPP/GA", "CT050-3-2-WAPP", "GA"),
    "BET150 A1 · Business Ethics (sample)": ("sample-assessments/BET150/A1", "BET150", "A1"),
    "DBS202 A1 · Database Systems (sample)": ("sample-assessments/DBS202/A1", "DBS202", "A1"),
    "DSA201 A1 · Data Structures & Algorithms (sample)": ("sample-assessments/DSA201/A1", "DSA201", "A1"),
    "DAN301 A2 · Data Analytics (sample)": ("sample-assessments/DAN301/A2", "DAN301", "A2"),
    "SEP310 A2 · Software Engineering PM (sample)": ("sample-assessments/SEP310/A2", "SEP310", "A2"),
}
REPLAY_SPEED = 3
UPLOAD = "Upload your own assignment"
UPLOAD_TYPES = ["pdf", "docx", "doc", "txt", "md"]
NO_RUBRIC = "(no separate rubric file was given: the marking scheme is inside the brief)"
NO_CLO = "(no CLO map was given: take the CLOs from the brief and the rubric)"

C = {"wait": ("#f3eee4", "#cfc5b6", "#7a6e62"), "run": ("#fbe3c4", "#c08a1e", "#231b14"),
     "done": ("#e6f0e3", "#3c7a4a", "#231b14"), "skip": ("#fcf9f2", "#cfc5b6", "#a59a8d"),
     "high": ("#f6dcd2", "#b65329", "#231b14"), "low": ("#e6f0e3", "#3c7a4a", "#231b14")}


def _saved_runs():
    out = {}
    for d in sorted(o.DEMO_RUNS.iterdir()):
        f = d / "06-verdict.json"
        if f.is_file():
            v = json.loads(f.read_text(encoding="utf-8"))
            out[f"{v.get('module')} {v.get('assessment')} · {v.get('module_name', '')} · {v.get('exposure')}"] = d.name
    return out


def _box(node, label, state, shape="box", style="rounded,filled"):
    fill, line, font = C[state]
    if state == "skip":
        style = "rounded,dashed"
    return (f'{node} [label=<{label}>, shape={shape}, style="{style}", fillcolor="{fill}", color="{line}", '
            f'fontcolor="{font}", penwidth={2.2 if state == "run" else 1.2}];')


def _dot(s):
    """The orchestration graph for the current state s = {status, results, trace, guard, exposure, approval}."""
    st_, res, tr = s["status"], s["results"], s["trace"]

    def lbl(i, extra=""):
        a = tr.get("agents", {}).get(i, {})
        name = f"<b>{o.BY_ID[i]['name']}</b>"
        if st_[i] == "run":
            return f"{name}<br/><font point-size='10'>working…</font>"
        if st_[i] == "skip":
            return f"{name}<br/><font point-size='10'>skipped: LOW</font>"
        if st_[i] == "done":
            retry = f" · {a.get('attempts')} tries" if a.get("attempts", 1) > 1 else ""
            return f"{name}<br/><font point-size='10'>{extra}{a.get('seconds', '')}s · schema ✓{retry}</font>"
        return name

    v = res.get("06-verdict", {})
    tot, grd = v.get("persona_totals", {}), v.get("persona_grades", {})

    def persona(p):
        return f"{grd.get(p)} {tot.get(p)}% · " if p in tot else ""

    ex = s.get("exposure")
    vstate = ("high" if ex in ("HIGH", "MEDIUM") else "low") if st_["06-verdict"] == "done" and ex else st_["06-verdict"]
    red = res.get("07-redesign")
    guard = s.get("guard") or ""
    gtxt = ("rule ✓" if "passed" in guard else "corrected" if guard else "exposure rule")
    lines = [
        "digraph G { rankdir=TB; bgcolor=transparent; nodesep=0.35; ranksep=0.32; size=\"9,7\";",
        'node [fontname="Helvetica", fontsize=13, margin="0.22,0.09", width=1.9]; edge [color="#9a8e80", arrowsize=0.7];',
        'IN [label=<<b>Lecturer files</b><br/><font point-size="10">brief · rubric · CLO map</font>>, shape=note, '
        'style=filled, fillcolor="#fffdfa", color="#cfc5b6"];',
        _box("I", lbl("01-intake"), st_["01-intake"]),
        "{ rank=same; " + " ".join([
            _box("P1", lbl("02-copy_paster", persona("copy_paster")), st_["02-copy_paster"]),
            _box("P2", lbl("02-prompt_engineer", persona("prompt_engineer")), st_["02-prompt_engineer"]),
            _box("P3", lbl("02-honest_helper", persona("honest_helper")), st_["02-honest_helper"])]) + " }",
        _box("E", lbl("05-examiner"), st_["05-examiner"]),
        "{ rank=same; " + _box("V", lbl("06-verdict", f"<b>{ex}</b> · " if ex else ""), vstate) + " "
        + _box("G", f"<b>Guardrail</b><br/><font point-size='10'>{gtxt}</font>", "done" if guard else "wait",
               shape="diamond", style="filled") + " }",
        "{ rank=same; " + _box("R", lbl("07-redesign", f"{len(red.get('options', []))} options · " if red else ""),
                                st_["07-redesign"]) + " "
        + _box("H", "<b>Lecturer approval</b><br/><font point-size='10'>" + s.get("approval", "human in the loop")
               + "</font>", "run" if s.get("approval") == "waiting for the lecturer" else "wait", style="filled,bold")
        + ' A [label=<<b>Jira · Gmail · Calendar</b><br/><font point-size="10">card · report · invite</font>>, '
        'shape=box, style="rounded,filled", fillcolor="#fffdfa", color="#cfc5b6"]; }',
        "IN -> I; I -> P1; I -> P2; I -> P3; P1 -> E; P2 -> E; P3 -> E; E -> V; V -> G [dir=both, arrowtail=none];",
        'V -> R [label=<<font point-size="9"> HIGH / MEDIUM</font>>]; R -> H; H -> A;',
        "}"]
    return "\n".join(lines)


def _files_from_upload(upload, read_upload):
    """The lecturer's own files -> the orchestrator's three text inputs (brief required, the rest optional)."""
    brief = read_upload(upload["brief"]).strip()
    if not brief:
        raise o.OrchestratorError("the brief file has no readable text (a scanned PDF? try the Word file or a text copy)")
    return {"brief.txt": brief,
            "rubric.txt": read_upload(upload["rubric"]).strip() or NO_RUBRIC,
            "clo-map.txt": read_upload(upload["clo"]).strip() or NO_CLO}


def _run(mode, choice, unlocked, upload=None, read_upload=None):
    state = {"status": {a["id"]: "wait" for a in o.AGENTS}, "results": {}, "trace": {"agents": {}}, "log": []}
    graph, log_box = st.empty(), st.empty()
    t0 = time.time()

    def log(line):
        state["log"].append(f"{time.time() - t0:5.1f}s  {line}")
        log_box.code("\n".join(state["log"][-14:]), language=None)

    def on_event(kind, i, info):
        if kind == "start":
            state["status"][i] = "run"
        elif kind == "done":
            state["status"][i] = "done"
            state["results"][i] = orch.results[i]
            state["trace"]["agents"][i] = info
            if i == "06-verdict":
                state["exposure"] = orch.results[i].get("exposure")
        elif kind == "guardrail":
            state["guard"] = info["text"]
            state["exposure"] = info["exposure"]
        elif kind == "skip":
            state["status"][i] = "skip"
        graph.graphviz_chart(_dot(state), use_container_width=True)

    graph.graphviz_chart(_dot(state), use_container_width=True)
    out = Path(tempfile.mkdtemp(prefix="redpen-agents-"))
    if mode == "replay":
        name = _saved_runs()[choice]
        backend = o.ReplayBackend(name, speed=REPLAY_SPEED)
        files = {"brief.txt": "(replay)", "rubric.txt": "(replay)", "clo-map.txt": "(replay)"}
        module, assessment = name, ""
        log(f"replay of saved run {name}: no API calls, real recorded timings sped up ×{REPLAY_SPEED}")
    elif choice == UPLOAD:
        files = _files_from_upload(upload, read_upload)
        module = (upload.get("module") or "MODULE").strip().upper()
        assessment = (upload.get("assessment") or "A1").strip().upper()
        backend = o.pick_backend("auto", None)
        log(f"live run on {backend.name} · your upload ({upload['brief'].name}) · "
            f"models: {', '.join(m.split('/')[-1] for m in backend.models)}")
    else:
        rel, module, assessment = LIVE_FOLDERS[choice]
        backend = o.pick_backend("auto", None)
        files = o.read_folder(o.ROOT / "data" / rel)
        log(f"live run on {backend.name} · models: {', '.join(m.split('/')[-1] for m in backend.models)}")
    orch = o.Orchestrator(backend, module, assessment, files, out, log=log, on_event=on_event)
    v = orch.run()
    state["approval"] = orch.trace["approval"]["status"]
    state["trace"] = orch.trace
    graph.graphviz_chart(_dot(state), use_container_width=True)
    log(f"done in {orch.trace['total_seconds']}s · verdict {v.get('exposure')} · "
        + ("waiting for the lecturer's approval" if "07-redesign" in orch.results else "no redesign needed"))
    st.session_state.agents_run = {"state": state, "results": orch.results, "trace": orch.trace, "mode": mode,
                                   "choice": choice, "brief": files.get("brief.txt", ""), "module": module,
                                   "assessment": assessment}
    st.session_state.agents_prompts = {a["id"]: orch.system_for(a) for a in o.AGENTS}


def _summary(run, ui):
    tr, res = run["trace"], run["results"]
    agents = tr.get("agents", {})
    retries = sum(a.get("attempts", 1) - 1 for a in agents.values())
    par = max((len(w) for w in tr.get("waves", [])), default=0)
    v = res.get("06-verdict", {})
    ui('<div class="rp-stats">'
       f'<div class="rp-stat"><b>{len(agents)}</b><span>Gemini agents ran</span></div>'
       f'<div class="rp-stat"><b>{len(tr.get("waves", []))}</b><span>waves · up to {par} in parallel</span></div>'
       f'<div class="rp-stat"><b>{tr.get("total_seconds", "?")}s</b><span>end to end'
       + (" (replay)" if run["mode"] == "replay" else "") + f' · {retries} self-correction'
       + ("" if retries == 1 else "s") + '</span></div></div>')
    clos = ", ".join(c.get("id", "?") for c in v.get("clos_at_risk", [])) or "none"
    ui(f'<div class="rp-para"><b>{html.escape(str(v.get("exposure")))} AI-exposure</b> · CLOs at risk: {clos}. '
       f'{html.escape(str(tr.get("guardrails", [""])[-1] if tr.get("guardrails") else ""))}.</div>')

    ui('<div class="rp-h">Every agent: its prompt and its output</div>')
    prompts = st.session_state.get("agents_prompts", {})
    for n, a in enumerate(o.AGENTS, 1):
        t = agents.get(a["id"])
        head = f"{n}. {a['name']}"
        if t:
            head += f" · {t['seconds']}s · {t['attempts']} attempt{'s' if t['attempts'] > 1 else ''} · schema ✓"
        elif a["id"] in tr.get("skipped", {}):
            head += " · skipped (exposure LOW)"
        with st.expander(head):
            st.caption(f"{a['job']} Prompt: `agents/{a['prompt']}` · output schema: `agents/schemas/{a['schema']}`")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Prompt**")
                st.code(prompts.get(a["id"], ""), language=None, height=380, wrap_lines=True)
            with c2:
                st.markdown("**Output**")
                if a["id"] in res:
                    st.json(res[a["id"]], expanded=1)
                else:
                    st.caption("Not run.")


def _to_lecturer(run):
    """Hand the live run to the Audit page as the lecturer's view: same verdict, same answers and marks, and the
    redesign the agent already wrote (no extra API call). Runs as a button callback, before the next rerun."""
    res = run["results"]
    v = dict(res["06-verdict"])
    v.setdefault("audit_date", dt.date.today().isoformat())
    v.setdefault("model", "flash")
    tag = "".join(ch for ch in f"{run.get('module', 'X')}-{run.get('assessment', 'A1')}" if ch.isalnum() or ch == "-")
    name = f"live-{tag}-{dt.datetime.now():%H%M%S}"
    st.session_state.live = {"result": {"verdict": v, "steps": dict(res)}, "brief": run.get("brief", ""), "name": name}
    if "07-redesign" in res:
        st.session_state[f"redesign-{name}"] = res["07-redesign"]
    st.session_state.page = "Audit"
    st.session_state.src = "New audit"
    st.session_state.step = "1  Verdict"


def page_agents(ui, unlocked, read_upload=None):
    ui('<div class="rp-title">Agent orchestration</div>')
    ui('<div class="rp-para">Seven Gemini agents audit one assignment. Intake runs first, the three AI students run '
       'in parallel, then the Examiner and the Verdict. Every output is checked against its schema and sent back to '
       'its agent if it fails. The exposure rule is enforced in code, the Redesign runs only for HIGH or MEDIUM, and '
       'nothing happens until the lecturer approves.</div>')
    live_ok = unlocked()
    modes = ["Replay a saved audit (instant, no API calls)"] + (["Run live on Gemini"] if live_ok else [])
    c1, c2 = st.columns([1, 2])
    mode_label = c1.radio("Mode", modes, key="agents_mode")
    mode = "live" if mode_label.startswith("Run live") else "replay"
    options = (list(LIVE_FOLDERS) + ([UPLOAD] if read_upload else [])) if mode == "live" else list(_saved_runs())
    default = next((i for i, k in enumerate(options) if k.startswith("CT074")), 0)
    choice = c2.selectbox("Assignment", options, index=default, key=f"agents_choice_{mode}")
    if not live_ok:
        c2.caption("Judge access unlocks live runs on Gemini.")
    upload = None
    if mode == "live" and choice == UPLOAD:
        u1, u2 = st.columns(2)
        upload = {"module": u1.text_input("Module code", placeholder="CT074-3-2", key="ag_module"),
                  "assessment": u2.text_input("Assessment", placeholder="A1", key="ag_assessment")}
        f1, f2, f3 = st.columns(3)
        upload["brief"] = f1.file_uploader("Assignment brief", type=UPLOAD_TYPES, key="ag_brief")
        upload["rubric"] = f2.file_uploader("Marking scheme (if separate)", type=UPLOAD_TYPES, key="ag_rubric")
        upload["clo"] = f3.file_uploader("Learning outcomes (if separate)", type=UPLOAD_TYPES, key="ag_clo")
    ran_now = False
    if st.button("Run the agents", type="primary", icon=":material/play_arrow:", key="agents_go",
                 disabled=bool(upload is not None and not upload["brief"])):
        try:
            _run(mode, choice, unlocked, upload, read_upload)
            ran_now = True
        except o.OrchestratorError as e:
            msg = ("Live runs are not set up on this server (no Gemini API key)" if "no API key" in str(e)
                   else f"The run stopped: {e}")
            st.error(f"{msg}. Use Replay to show a saved run.")
            return
        except Exception as e:  # never show judges a traceback
            st.error(f"The run stopped unexpectedly ({type(e).__name__}: {str(e)[:200]}). Use Replay to show a saved run.")
            return
    run = st.session_state.get("agents_run")
    if run:
        if not ran_now:  # a rerun (for example opening an expander): redraw the finished graph
            st.graphviz_chart(_dot(run["state"]), use_container_width=True)
        st.caption(("Replay of a saved audit: the real outputs and recorded timings of an earlier Gemini run, sped up. "
                    if run["mode"] == "replay" else "Live run on Gemini. ") + f"Assignment: {run['choice']}")
        if run["mode"] == "live" and "06-verdict" in run["results"]:
            at_risk = run["results"]["06-verdict"].get("exposure") in ("HIGH", "MEDIUM")
            st.button("Continue as the lecturer: fix and approve" if at_risk else "Open the lecturer's view",
                      type="primary", icon=":material/arrow_forward:", key="agents_to_lecturer",
                      on_click=_to_lecturer, args=(run,))
        _summary(run, ui)
    else:
        st.graphviz_chart(_dot({"status": {a["id"]: "wait" for a in o.AGENTS}, "results": {}, "trace": {}}),
                          use_container_width=True)
