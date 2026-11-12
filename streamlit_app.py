"""RedPen prototype app (Streamlit).

Run locally:  streamlit run streamlit_app.py
Hosted:       Streamlit Community Cloud, main file streamlit_app.py, secrets as in docs/api-keys.md.

The agents are the prompts in agents/ (the same text pasted into Gemini Enterprise for the final build).
"""
import datetime as dt
import io
import json
import os
import pathlib
import sys

import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

# Streamlit secrets -> environment, before the engine reads them.
try:
    for k, v in st.secrets.items():
        if isinstance(v, (str, int, float)) and k not in os.environ:
            os.environ[k] = str(v)
except Exception:  # no secrets file locally
    pass

import redpen_audit as ra  # noqa: E402
import redpen_fix as rf  # noqa: E402

st.set_page_config(page_title="RedPen", page_icon="🖍️", layout="wide")

EXPOSURE_STYLE = {"HIGH": ("#b91c1c", "#fee2e2"), "MEDIUM": ("#b45309", "#fef3c7"), "LOW": ("#15803d", "#dcfce7")}
PERSONA_NAMES = {"copy_paster": "Copy-paster", "prompt_engineer": "Prompt engineer", "honest_helper": "Honest helper"}
PERSONA_HELP = {"copy_paster": "pastes the brief into a chatbot and submits the answer as is",
                "prompt_engineer": "plans, drafts and self-critiques with AI",
                "honest_helper": "uses AI only the way the brief allows"}
PILOT = {"CCP_A1", "DSTR_LW1", "DSTR_LW2", "WAPP_GA"}

st.markdown("""<style>
.badge{display:inline-block;padding:.35rem .9rem;border-radius:999px;font-weight:800;font-size:1.1rem}
.small{color:#64748b;font-size:.9rem}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def read_upload(f):
    if f is None:
        return ""
    data = f.getvalue()
    name = f.name.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        out = [p.text for p in d.paragraphs]
        for t in d.tables:
            out += [" | ".join(c.text for c in r.cells) for r in t.rows]
        return "\n".join(out)
    return data.decode("utf-8", errors="replace")


def demo_label(name):
    r = ra.load_demo(name)
    v = r["verdict"]
    tag = "real APU brief" if name in PILOT else "sample brief"
    return f"{v.get('module')} {v.get('assessment')} · {v.get('module_name', '')} · {v.get('exposure')} ({tag})"


def badge(exposure):
    fg, bg = EXPOSURE_STYLE.get(exposure, ("#334155", "#e2e8f0"))
    return f'<span class="badge" style="color:{fg};background:{bg}">{exposure} AI-exposure</span>'


def unlocked():
    pw = os.environ.get("APP_PASSWORD", "")
    return not pw or st.session_state.get("pw_ok", False)


def show_verdict(result):
    v, steps = result["verdict"], result["steps"]
    st.markdown(badge(v.get("exposure", "?")), unsafe_allow_html=True)
    st.subheader(f"{v.get('module')} {v.get('assessment')}: {v.get('module_name', '')}")
    st.write(v.get("summary", ""))

    cols = st.columns(3)
    for col, p in zip(cols, PERSONA_NAMES):
        with col:
            total = v.get("persona_totals", {}).get(p)
            st.metric(PERSONA_NAMES[p], f"{v.get('persona_grades', {}).get(p, '-')}  ·  {total}%",
                      delta="passes" if (total or 0) >= v.get("pass_mark", 50) else "fails",
                      delta_color="inverse" if p != "honest_helper" else "off")
            st.caption(PERSONA_HELP[p])
    st.caption(f"Pass mark {v.get('pass_mark')}% · audit {v.get('audit_date')} · model: Gemini {v.get('model')}")

    if v.get("clos_at_risk"):
        st.markdown("**Learning outcomes this assessment no longer reliably proves**")
        for c in v["clos_at_risk"]:
            st.error(f"**{c.get('id')}**: {c.get('text')}  \n{c.get('why', '')}")
    else:
        st.success("No learning outcomes at risk: the AI students could not pass.")
    if v.get("easy_criteria"):
        st.markdown("**Rubric criteria the AI met easily:** " + ", ".join(v["easy_criteria"]))

    with st.expander("See what each AI student submitted and how the Examiner marked it"):
        ex = {r.get("persona"): r for r in steps.get("05-examiner", {}).get("results", [])}
        for p in PERSONA_NAMES:
            st.markdown(f"#### {PERSONA_NAMES[p]}")
            for s in ex.get(p, {}).get("scores", []):
                st.markdown(f"- **{s.get('criterion')}**: {s.get('score')}/{s.get('max')}. {s.get('justification', '')}")
            ans = steps.get(f"02-{p}", {}).get("answers", [])
            for a in ans:
                st.text_area(f"{PERSONA_NAMES[p]}, task {a.get('task_id')}", a.get("answer", ""), height=160,
                             key=f"ans-{p}-{a.get('task_id')}-{id(result)}")
    with st.expander("Raw verdict JSON (the hand-off file between the Audit and Fix workflows)"):
        st.json(v)


def show_fix(result, brief_text, name):
    v = result["verdict"]
    if v.get("exposure") not in ("HIGH", "MEDIUM"):
        st.info("LOW exposure: no redesign needed. It is still logged in the register and re-audited monthly.")
        return
    st.markdown("---")
    st.header("2 · Fix: redesign options that keep the same learning outcomes")
    key = f"redesign-{name}"
    if key not in st.session_state:
        saved = rf.demo_redesign(name) if name else None
        if saved:
            st.session_state[key] = saved
    if key not in st.session_state:
        if st.button("Propose redesigns", type="primary", disabled=not unlocked()):
            with st.spinner("Redesign agent is working..."):
                try:
                    st.session_state[key] = rf.run_redesign(v, brief_text)
                except ra.AuditError as e:
                    st.error(f"Redesign failed: {e}")
                    return
        else:
            return
    red = st.session_state[key]
    opts = red.get("options", [])
    st.write(red.get("why_recommended", ""))
    ids = [o.get("id") for o in opts]
    pick = st.radio("Choose a redesign", ids, index=ids.index(red.get("recommended")) if red.get("recommended") in ids else 0,
                    format_func=lambda i: next(f"{o['id']}: {o.get('title')}" + (" (recommended)" if i == red.get("recommended") else "")
                                               for o in opts if o["id"] == i), horizontal=True)
    opt = rf.option(red, pick)
    c1, c2, c3 = st.columns(3)
    c1.metric("AIAS level", opt.get("aias_level"))
    c2.metric("Lane", str(opt.get("lane", "")).title())
    c3.metric("Extra marking per student", f"{opt.get('extra_marking_minutes_per_student')} min")
    st.markdown("**Techniques:** " + ", ".join(opt.get("techniques", [])))
    for c in opt.get("clo_coverage", []):
        st.markdown(f"- **{c.get('id')}** still assessed: {c.get('how')}")
    st.text_area("Revised task text", opt.get("revised_task_text", ""), height=180, key=f"rt-{name}-{pick}")

    st.markdown("---")
    st.header("3 · Lecturer approval (human in the loop)")
    st.caption("Nothing is changed, logged or sent until the lecturer approves.")
    to = st.text_input("Lecturer email", value=v.get("lecturer_email", "") if "@" in v.get("lecturer_email", "") and
                       "REPLACE" not in v.get("lecturer_email", "") else os.environ.get("DEMO_LECTURER_EMAIL", ""))
    if st.button(f"✅ Approve {pick}", type="primary", disabled=not unlocked()):
        do_actions(v, red, opt, brief_text, to, name)
    if st.session_state.get(f"done-{name}"):
        show_downloads(v, red, opt, brief_text, name)


def do_actions(v, red, opt, brief_text, to, name):
    log = []
    revised = rf.revised_brief(brief_text, v, opt)
    ics = rf.ics_invite(v, to) if v.get("exposure") == "HIGH" else None
    if rf.jira_configured():
        try:
            k, url, how = rf.jira_upsert(v, opt)
            log.append(("Jira", f"{how} [{k}]({url}) in the Assessment Exposure Register, labels {', '.join(rf.jira_labels(v))}"))
        except ra.AuditError as e:
            log.append(("Jira", f"⚠️ {e}"))
    else:
        log.append(("Jira", "not configured here (set JIRA_* secrets). Card that would be created: "
                            f"**{v.get('module')} {v.get('assessment')}**, labels {', '.join(rf.jira_labels(v))}"))
    if rf.smtp_configured() and to:
        try:
            att = [(f"{v.get('module')}_{v.get('assessment')}_revised.txt", revised.encode(), "text/plain")]
            if ics:
                att.append(("redpen-review.ics", ics.encode(), "text/calendar"))
            rf.send_email(to, rf.email_subject(v), rf.email_body(v, red, opt), att)
            log.append(("Email", f"report sent to {to}" + (" with the review invite" if ics else "")))
        except Exception as e:  # noqa: BLE001
            log.append(("Email", f"⚠️ {e}"))
    else:
        log.append(("Email", "not sent (no SMTP secrets or no address). Preview and download below."))
    if ics:
        log.append(("Calendar", f"30-min T&L review invite for {rf.next_working_day_10am():%a %d %b, 10:00} (download below)"))
    log.append(("Revised brief", "ready to download below"))
    st.session_state[f"done-{name}"] = log


def show_downloads(v, red, opt, brief_text, name):
    st.success("Approved. RedPen did the follow-up:")
    for what, msg in st.session_state[f"done-{name}"]:
        st.markdown(f"- **{what}:** {msg}")
    base = f"{v.get('module')}_{v.get('assessment')}"
    c1, c2, c3 = st.columns(3)
    c1.download_button("Revised brief (.txt)", rf.revised_brief(brief_text, v, opt), f"{base}_revised.txt")
    if v.get("exposure") == "HIGH":
        c2.download_button("Review invite (.ics)", rf.ics_invite(v), "redpen-review.ics", mime="text/calendar")
    c3.download_button("Verdict (.json)", json.dumps(v, indent=2), f"{base}_verdict.json", mime="application/json")
    with st.expander("Email to the lecturer"):
        st.markdown(f"**Subject:** {rf.email_subject(v)}")
        st.text(rf.email_body(v, red, opt))


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("## 🖍️ RedPen")
    st.caption("They catch students. We fix assignments.")
    mode = st.radio("Mode", ["Saved audits (instant)", "Run a new audit"], index=0)
    st.markdown("---")
    if os.environ.get("APP_PASSWORD") and not st.session_state.get("pw_ok"):
        pw = st.text_input("Password for live runs", type="password")
        if pw:
            st.session_state.pw_ok = pw == os.environ["APP_PASSWORD"]
            if not st.session_state.pw_ok:
                st.error("Wrong password")
    if unlocked():
        with st.expander("API key (Gemini only)"):
            try:
                st.caption(f"Backend: **{ra.backend()}** · models: {', '.join(ra.models())}")
            except ra.AuditError as e:
                st.error(str(e))
            new_key = st.text_input("Swap key (OpenRouter sk-or-… or Google AI Studio)", type="password")
            if st.button("Use this key") and new_key:
                try:
                    ra.set_credentials(new_key)
                    st.success(f"Now using {ra.backend()}")
                except ra.AuditError as e:
                    st.error(str(e))
            if st.button("Test models"):
                with st.spinner("One tiny call per model..."):
                    for m, s in ra.check_models():
                        st.write(f"`{m}`: {s}")
    st.markdown("---")
    st.caption("Agents: Intake → 3 AI students → Examiner → Verdict → Redesign → lecturer approval → Jira, email, calendar. "
               "Same prompts as our Gemini Enterprise workflows.")

st.title("RedPen: an AI red team for your assessments")
st.caption("Before students get AI to do the assignment, RedPen already has, and tells you which learning outcomes you can no longer trust.")

# ------------------------------------------------------------------ main
if mode.startswith("Saved"):
    runs = ra.demo_runs()
    order = sorted(runs, key=lambda n: (n not in PILOT, n))
    name = st.selectbox("Choose an audited assessment", order, format_func=demo_label)
    result = ra.load_demo(name)
    st.header("1 · Audit: three AI students attempt it, an AI examiner marks it")
    show_verdict(result)
    show_fix(result, rf.brief_for_demo(name, result["steps"].get("01-intake", {})), name)

    st.markdown("---")
    st.header("Assessment Exposure Register")
    rows = []
    for n in order:
        v = ra.load_demo(n)["verdict"]
        rows.append({"Assessment": f"{v.get('module')} {v.get('assessment')}", "Brief": "real APU" if n in PILOT else "sample",
                     "Exposure": v.get("exposure"), "Copy-paster": f"{v['persona_grades'].get('copy_paster')} ({v['persona_totals'].get('copy_paster')}%)",
                     "CLOs at risk": ", ".join(c.get("id", "") for c in v.get("clos_at_risk", [])) or "-"})
    st.dataframe(rows, hide_index=True, width="stretch")
else:
    if not unlocked():
        st.warning("Enter the password in the sidebar to run a live audit (each run uses 6 Gemini calls). "
                   "Saved audits work without it.")
        st.stop()
    st.header("1 · Audit a new assessment")
    c1, c2 = st.columns(2)
    module = c1.text_input("Module code", "DEMO101")
    assessment = c2.text_input("Assessment", "A1")
    brief_f = st.file_uploader("Assignment brief", type=["txt", "pdf", "docx", "md"])
    rubric_f = st.file_uploader("Marking rubric", type=["txt", "pdf", "docx", "md"])
    clo_f = st.file_uploader("CLO map (optional)", type=["txt", "pdf", "docx", "md"])
    email = st.text_input("Lecturer email (optional)")
    if st.button("Run the red team", type="primary", disabled=not (brief_f and rubric_f)):
        brief, rubric, clo = read_upload(brief_f), read_upload(rubric_f), read_upload(clo_f) or "(no CLO map given)"
        status = st.status("Auditing... (about 1-5 minutes)", expanded=True)

        def on_step(n, d, secs):
            status.write(f"✓ {ra.STEP_TITLES.get(n, n)} ({secs:.0f}s)")
        try:
            res = ra.run_audit(brief, rubric, clo, module.strip().upper(), assessment.strip().upper(),
                               lecturer_email=email or None, on_step=on_step)
            status.update(label="Audit complete", state="complete")
            st.session_state.live = {"result": res, "brief": brief, "name": f"live-{module}-{assessment}-{dt.datetime.now():%H%M%S}"}
        except ra.AuditError as e:
            status.update(label="Audit failed", state="error")
            st.error(f"{e}. Try 'Test models' in the sidebar, or use Saved audits.")
    live = st.session_state.get("live")
    if live:
        show_verdict(live["result"])
        show_fix(live["result"], live["brief"], live["name"])

st.markdown("---")
st.caption("RedPen is a risk signal from simulated AI attempts marked by an AI examiner (calibrated: 7 of 7 real assignments "
           "within one grade band of independent reference marks). It never sees or judges real student work.")
