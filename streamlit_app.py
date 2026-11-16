"""RedPen app (Streamlit).

Run locally:  streamlit run streamlit_app.py
Hosted:       Streamlit Community Cloud, main file streamlit_app.py, secrets as in docs/api-keys.md.

The agents are the prompts in agents/ (the same text pasted into Gemini Enterprise for the final build).
Layout: sidebar menu (Audit, Register, How it works). The Audit page leads with a report banner (risk ring + one-line
verdict), then one step at a time: Verdict, Fix, Approve. Explanations live on the How it works page, not in captions.
"""
import csv
import datetime as dt
import html
import io
import json
import os
import pathlib
import re
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

PERSONAS = {"copy_paster": "Copy-paster", "prompt_engineer": "Prompt engineer", "honest_helper": "Honest helper"}
PERSONA_HELP = {"copy_paster": "Pastes the brief into a chatbot and submits the answer as it is.",
                "prompt_engineer": "Uses AI strategically: plans, drafts and self-critiques.",
                "honest_helper": "Uses AI only the way the brief allows, and leaves the student’s own parts blank."}
PILOT = {"CCP_A1", "DSTR_LW1", "DSTR_LW2", "WAPP_GA"}
HEADLINE = {"HIGH": "A student can pass this by pasting the brief into AI.",
            "MEDIUM": "A student who uses AI cleverly can pass this.",
            "LOW": "AI alone can’t pass this assignment."}
TONE = {"HIGH": "#b65329", "MEDIUM": "#c08a1e", "LOW": "#3c7a4a"}
STEPS = ["1  Verdict", "2  Fix", "3  Approve"]

# ------------------------------------------------------------------ styles (RedPen brand: cream, terracotta, Fraunces + Geist)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Geist:wght@400;500;600;700&display=swap');
:root{--bg:#fcf9f2;--fg:#231b14;--fg2:#4a4039;--card:#fffdfa;--muted:#7a6e62;--border:#e6dfd3;--input:#cfc5b6;--subtle:#f3eee4;
  --primary:#b65329;--primary-fg:#fffdfa;--serif:'Fraunces',Georgia,serif;--sans:'Geist',ui-sans-serif,system-ui,sans-serif}
html,body,[class*="st-"],.stMarkdown,button,input,textarea,select{font-family:var(--sans)!important}
[data-testid="stIconMaterial"],[data-testid="stExpanderIcon"],.material-symbols-rounded{font-family:'Material Symbols Rounded'!important}
.stApp{background:var(--bg)!important}
header[data-testid="stHeader"]{background:transparent!important;height:2.5rem}
#MainMenu,footer,[data-testid="stDecoration"]{display:none!important}
[data-testid="stMainBlockContainer"],.block-container{max-width:1000px;padding-top:1.2rem!important;padding-bottom:4rem}
h1,h2,h3,h4{color:var(--fg);font-family:var(--serif)!important;letter-spacing:-.02em}
/* sidebar: brand + menu */
[data-testid="stSidebar"]{background:#f6f1e7!important;border-right:1px solid var(--border)}
[data-testid="stSidebarHeader"]{position:absolute!important;top:1.15rem;right:.6rem;height:auto!important;min-height:0!important;padding:0!important;margin:0!important;z-index:5;width:auto!important}
[data-testid="stSidebarUserContent"]{padding-top:1.25rem!important}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.2rem!important}
[data-testid="stSidebar"] [role="radiogroup"]>div,[data-testid="stSidebar"] [data-testid="stRadioOption"]{width:100%}
[data-testid="stSidebar"] [data-testid="stRadioOption"]{padding:.55rem .75rem;border-radius:10px;margin:0!important;cursor:pointer}
[data-testid="stSidebar"] [data-testid="stRadioOption"]>div>div:first-child{display:none!important}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]{background:#fffdfa;box-shadow:inset 3px 0 0 var(--primary)}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p{color:var(--fg)!important;font-weight:600!important}
[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:.98rem!important;font-weight:500!important;color:var(--fg2)!important}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#fffdfa;box-shadow:inset 3px 0 0 var(--primary)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:var(--fg)!important;font-weight:600!important}
.rp-brand{display:flex;align-items:center;gap:.6rem;margin:0 0 1.2rem 0;min-height:2rem}
.rp-logo{width:2rem;height:2rem;border-radius:9px;background:var(--primary);display:flex;align-items:center;justify-content:center;font-size:1rem}
.rp-brand span{font-family:var(--serif);font-size:1.3rem;font-weight:600;letter-spacing:-.01em;color:var(--fg)}
/* inputs + buttons */
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{background:#fff!important;border:1px solid var(--input)!important;border-radius:10px!important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within{border-color:var(--primary)!important;box-shadow:0 0 0 3px rgba(182,83,41,.15)!important}
[data-baseweb="input"] input,[data-baseweb="base-input"],[data-baseweb="input"] button{background:transparent!important;border:none!important}
[data-testid="InputInstructions"]{display:none!important}
[data-testid="stWidgetLabel"] p{font-size:.88rem!important;font-weight:500!important;color:var(--fg2)!important}
.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:999px!important;font-weight:500!important;min-height:2.6rem;
  border:1px solid var(--input)!important;background:#fff!important;color:var(--fg)!important;box-shadow:none!important}
.stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{border-color:#a89b89!important;background:var(--subtle)!important;color:var(--fg)!important}
.stButton>button[kind="primary"]{background:var(--primary)!important;border-color:var(--primary)!important;padding:0 1.5rem!important}
.stButton>button[kind="primary"],.stButton>button[kind="primary"] *{color:var(--primary-fg)!important}
.stButton>button[kind="primary"]:hover{background:#9f4722!important}
/* step switcher */
[data-testid="stButtonGroup"] button{border-radius:999px!important;font-weight:500!important;padding:0 1.1rem!important;min-height:2.4rem}
[data-testid="stButtonGroup"] button[kind*="Active"],[data-testid="stButtonGroup"] button[aria-checked="true"]{background:var(--primary)!important;border-color:var(--primary)!important}
[data-testid="stButtonGroup"] button[kind*="Active"] *,[data-testid="stButtonGroup"] button[aria-checked="true"] *{color:var(--primary-fg)!important}
[data-testid="stExpander"] details{border-radius:12px!important;border-color:var(--border)!important;background:var(--card)}
[data-testid="stExpander"] summary p{font-weight:500;font-size:.95rem}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:12px;overflow:hidden;background:#fff}
hr{margin:1.4rem 0!important;border-color:var(--border)!important}
/* report banner */
.rp-banner{display:flex;gap:1.8rem;align-items:center;background:var(--card);border:1px solid var(--border);border-radius:18px;padding:1.6rem 1.8rem;margin:.6rem 0 1.4rem 0}
.rp-ring{flex:none;width:118px;height:118px;position:relative}
.rp-ring svg{width:118px;height:118px}
.rp-ring div{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-weight:700;font-size:1.35rem;letter-spacing:.02em}
.rp-code{font-size:.85rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.rp-name{font-family:var(--serif);font-weight:600;font-size:1.75rem;line-height:1.2;color:var(--fg);margin:.15rem 0 .45rem 0}
.rp-say{font-size:1.12rem;line-height:1.5;color:var(--fg2)}
/* persona tiles */
.rp-tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem;margin:.4rem 0 1.4rem 0}
.rp-tile{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.1rem 1.2rem}
.rp-tile .t{font-weight:600;font-size:.95rem;color:var(--fg)}
.rp-tile .g{font-family:var(--serif);font-weight:600;font-size:2.5rem;line-height:1;margin:.7rem 0 .2rem 0;color:var(--fg)}
.rp-tile .g span{font-family:var(--sans);font-size:1rem;font-weight:500;color:var(--muted);margin-left:.4rem}
.rp-tile .s{font-size:.85rem;font-weight:600;margin-top:.7rem}
.rp-bar{position:relative;height:7px;border-radius:999px;background:var(--subtle);margin-top:.8rem}
.rp-bar i{position:absolute;left:0;top:0;bottom:0;border-radius:999px}
.rp-bar b{position:absolute;top:-5px;bottom:-5px;width:2px;background:var(--fg);border-radius:2px}
.rp-h{font-family:var(--serif);font-weight:600;font-size:1.3rem;color:var(--fg);margin:1.2rem 0 .5rem 0}
.rp-clo{display:flex;gap:1rem;align-items:baseline;padding:.75rem 0;border-top:1px solid var(--border);font-size:1rem;color:var(--fg2);line-height:1.5}
.rp-clo:last-child{border-bottom:1px solid var(--border)}
.rp-clo b{flex:none;color:var(--primary);font-weight:700;min-width:3.2rem}
.rp-ok{padding:.9rem 1.1rem;border-radius:12px;background:#eef5ec;color:#2f5f3a;font-weight:500}
.rp-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem;margin:.5rem 0 1rem 0}
.rp-stat{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1rem 1.2rem}
.rp-stat b{display:block;font-family:var(--serif);font-weight:600;font-size:2rem;line-height:1.1;color:var(--fg)}
.rp-stat span{font-size:.9rem;color:var(--muted)}
.rp-check{display:flex;gap:.7rem;align-items:flex-start;padding:.5rem 0;font-size:1rem;color:var(--fg2)}
.rp-check>i{flex:none;width:1.3rem;height:1.3rem;border-radius:999px;background:var(--primary);color:#fff;font-style:normal;font-size:.75rem;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:.15rem}
.rp-check b{color:var(--fg)}
.rp-check a{color:var(--primary)}
.rp-pre{white-space:pre-wrap;font-size:.92rem;line-height:1.6;color:var(--fg2)}
.rp-title{font-family:var(--serif);font-weight:600;font-size:2.2rem;letter-spacing:-.02em;color:var(--fg);margin:.4rem 0 1rem 0}
/* how it works */
.rp-flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem;margin:.4rem 0 1.4rem 0}
.rp-flow div{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.1rem 1.2rem}
.rp-flow em{display:inline-flex;width:1.8rem;height:1.8rem;border-radius:999px;background:rgba(182,83,41,.1);color:var(--primary);font-style:normal;font-weight:700;font-size:.85rem;align-items:center;justify-content:center}
.rp-flow b{display:block;font-family:var(--serif);font-size:1.15rem;margin:.6rem 0 .25rem 0;color:var(--fg)}
.rp-flow p{margin:0;font-size:.95rem;color:var(--fg2);line-height:1.5}
@media (max-width:760px){.rp-tiles,.rp-stats,.rp-flow{grid-template-columns:1fr}.rp-banner{flex-direction:column;align-items:flex-start}}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def esc(x):
    return html.escape(str(x if x is not None else ""))


def ui(markup):
    st.markdown(markup, unsafe_allow_html=True)


def pre(x):
    return esc(x).replace("\r", "").replace("\n", "<br>")


def human(x):
    for k, n in PERSONAS.items():
        x = str(x).replace(k, n.lower())
    return x


def md_inline(x):
    x = esc(x)
    x = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", x)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank">\1</a>', x)


def read_upload(f):
    if f is None:
        return ""
    data, name = f.getvalue(), f.name.lower()
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


def unlocked():
    pw = os.environ.get("APP_PASSWORD", "")
    return not pw or st.session_state.get("pw_ok", False)


def past_label(name):
    v = ra.load_demo(name)["verdict"]
    return f"{v.get('module')} {v.get('assessment')} · {v.get('module_name', '')}" + ("" if name in PILOT else " (sample)")


def set_step(i):
    st.session_state.step = STEPS[i]


def reset_step():
    st.session_state.step = STEPS[0]


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    ui('<div class="rp-brand"><div class="rp-logo">🖍️</div><span>RedPen</span></div>')
    page = st.radio("Menu", ["Audit", "Register", "How it works"], label_visibility="collapsed", key="page")
    st.divider()
    if os.environ.get("APP_PASSWORD") and not st.session_state.get("pw_ok"):
        pw = st.text_input("Judge access", type="password", placeholder="Access code")
        if pw:
            st.session_state.pw_ok = pw == os.environ["APP_PASSWORD"]
            if st.session_state.pw_ok:
                st.rerun()
            st.error("Wrong code")
    elif os.environ.get("APP_PASSWORD"):
        st.success("Judge access on", icon=":material/lock_open:")
    if unlocked():
        with st.expander("API key"):
            try:
                st.caption(", ".join(m.split("/")[-1] for m in ra.models()))
            except ra.AuditError as e:
                st.error(str(e))
            new_key = st.text_input("OpenRouter key", type="password", placeholder="sk-or-…")
            if st.button("Use this key") and new_key:
                try:
                    ra.set_credentials(new_key)
                    st.success("Key in use")
                except ra.AuditError as e:
                    st.error(str(e))
            if st.button("Test models"):
                with st.spinner("Testing…"):
                    for m, s in ra.check_models():
                        st.write(f"`{m.split('/')[-1]}`: {s}")


# ------------------------------------------------------------------ audit: banner + steps
def banner(v):
    exp = v.get("exposure", "LOW")
    c = TONE.get(exp, "#7a6e62")
    arc = {"HIGH": 327, "MEDIUM": 218, "LOW": 109}.get(exp, 0)
    ui(f'<div class="rp-banner"><div class="rp-ring"><svg viewBox="0 0 120 120">'
       f'<circle cx="60" cy="60" r="52" fill="none" stroke="#efe8dc" stroke-width="10"/>'
       f'<circle cx="60" cy="60" r="52" fill="none" stroke="{c}" stroke-width="10" stroke-linecap="round" '
       f'stroke-dasharray="{arc} 327" transform="rotate(-90 60 60)"/></svg>'
       f'<div style="color:{c}">{esc(exp)}</div></div>'
       f'<div><div class="rp-code">{esc(v.get("module"))} {esc(v.get("assessment"))}</div>'
       f'<div class="rp-name">{esc(v.get("module_name", ""))}</div>'
       f'<div class="rp-say">{HEADLINE.get(exp, "")}</div></div></div>')


def step_verdict(cur):
    v, steps = cur["result"]["verdict"], cur["result"]["steps"]
    pm = v.get("pass_mark", 50) or 50
    tiles = []
    for p, n in PERSONAS.items():
        total = v.get("persona_totals", {}).get(p) or 0
        passed = total >= pm
        col = "#b65329" if (passed and p != "honest_helper") else "#8a7d6e"
        tiles.append(f'<div class="rp-tile"><div class="t">{n}</div>'
                     f'<div class="g">{esc(v.get("persona_grades", {}).get(p, "–"))}<span>{total}%</span></div>'
                     f'<div class="rp-bar"><i style="width:{min(total, 100)}%;background:{col}"></i><b style="left:{pm}%"></b></div>'
                     f'<div class="s" style="color:{col}">{"Passes" if passed else "Fails"}</div></div>')
    ui('<div class="rp-tiles">' + "".join(tiles) + '</div>')

    clos = v.get("clos_at_risk") or []
    if clos:
        ui('<div class="rp-h">No longer proven</div>' +
           "".join(f'<div class="rp-clo"><b>{esc(c.get("id"))}</b><span>{esc(c.get("text"))}</span></div>' for c in clos))
    else:
        ui('<div class="rp-ok">Every learning outcome is still proven.</div>')

    st.write("")
    with st.expander("Evidence", icon=":material/description:"):
        ex = {r.get("persona"): r for r in steps.get("05-examiner", {}).get("results", [])}
        for p, n in PERSONAS.items():
            st.markdown(f"**{n}**")
            for s in ex.get(p, {}).get("scores", []):
                st.markdown(f"- {s.get('criterion')}: **{s.get('score')}/{s.get('max')}**. {s.get('justification', '')}")
            for a in steps.get(f"02-{p}", {}).get("answers", []):
                st.text_area(f"{n}, task {a.get('task_id')}", a.get("answer", ""), height=150,
                             key=f"ans-{p}-{a.get('task_id')}-{cur['name']}")
        st.download_button("Verdict file (.json)", json.dumps(v, indent=2),
                           f"{v.get('module')}_{v.get('assessment')}_verdict.json", mime="application/json",
                           key=f"vj-{cur['name']}")
    st.write("")
    if v.get("exposure") in ("HIGH", "MEDIUM"):
        st.button("Fix this assignment", type="primary", icon=":material/arrow_forward:", on_click=set_step, args=(1,))


def redesign_for(cur):
    key = f"redesign-{cur['name']}"
    if key not in st.session_state and not cur["name"].startswith("live-"):
        saved = rf.demo_redesign(cur["name"])
        if saved:
            st.session_state[key] = saved
    return st.session_state.get(key), key


def brief_of(cur):
    return cur.get("brief") or rf.brief_for_demo(cur["name"], cur["result"]["steps"].get("01-intake", {}))


def step_fix(cur):
    v = cur["result"]["verdict"]
    if v.get("exposure") not in ("HIGH", "MEDIUM"):
        ui('<div class="rp-ok">Nothing to fix.</div>')
        return
    red, key = redesign_for(cur)
    if red is None:
        if st.button("Suggest fixes", type="primary", icon=":material/auto_fix_high:", disabled=not unlocked()):
            with st.spinner("Writing fixes…"):
                try:
                    st.session_state[key] = rf.run_redesign(v, brief_of(cur))
                    st.rerun()
                except ra.AuditError as e:
                    st.error(f"Couldn’t write fixes: {e}")
        return
    opts = red.get("options", [])
    ids = [o.get("id") for o in opts]
    rec = red.get("recommended")
    pick = st.radio("Choose a fix", ids, index=ids.index(rec) if rec in ids else 0, key=f"pick-{cur['name']}",
                    format_func=lambda i: next(o.get("title", i) for o in opts if o["id"] == i) + ("  · recommended" if i == rec else ""))
    opt = rf.option(red, pick)
    ui('<div class="rp-stats">'
       f'<div class="rp-stat"><b>+{esc(opt.get("extra_marking_minutes_per_student"))} min</b><span>marking per student</span></div>'
       f'<div class="rp-stat"><b>{esc(str(opt.get("lane", "")).title())}</b><span>lane</span></div>'
       f'<div class="rp-stat"><b>Level {esc(opt.get("aias_level"))}</b><span>AI Assessment Scale</span></div></div>')
    if opt.get("clo_coverage"):
        ui('<div class="rp-h">Still tests</div>' +
           "".join(f'<div class="rp-clo"><b>{esc(c.get("id"))}</b><span>{esc(c.get("how"))}</span></div>' for c in opt["clo_coverage"]))
    st.write("")
    with st.expander("Revised task", icon=":material/description:"):
        ui(f'<div class="rp-pre">{pre(opt.get("revised_task_text", ""))}</div>')
    st.write("")
    st.button("Continue to approval", type="primary", icon=":material/arrow_forward:", on_click=set_step, args=(2,))


def step_approve(cur):
    v = cur["result"]["verdict"]
    name = cur["name"]
    red, _ = redesign_for(cur)
    if v.get("exposure") not in ("HIGH", "MEDIUM") or red is None:
        ui('<div class="rp-ok">Pick a fix first.</div>')
        return
    opt = rf.option(red, st.session_state.get(f"pick-{name}"))
    high = v.get("exposure") == "HIGH"
    ui('<div class="rp-h" style="margin-top:.2rem">On approval, RedPen will</div>'
       '<div class="rp-check"><i>1</i><span>Add the card to the <b>Jira</b> exposure register</span></div>'
       '<div class="rp-check"><i>2</i><span>Email the report and revised brief with <b>Gmail</b></span></div>'
       + ('<div class="rp-check"><i>3</i><span>Book a 30-minute review in <b>Google Calendar</b></span></div>' if high else ''))
    st.write("")
    c1, c2 = st.columns([3, 1.2], vertical_alignment="bottom")
    to = c1.text_input("Lecturer email", value=os.environ.get("DEMO_LECTURER_EMAIL", ""),
                       placeholder="lecturer@university.edu.my", key=f"to-in-{name}")
    if c2.button(f"Approve {opt.get('id', '')}" + ("" if unlocked() else " (preview)"), type="primary",
                 icon=":material/check:", width="stretch"):
        do_actions(v, red, opt, brief_of(cur), to, name)
    if st.session_state.get(f"done-{name}"):
        show_done(cur, red, opt)


def do_actions(v, red, opt, brief, to, name):
    log = []
    revised = rf.revised_brief(brief, v, opt)
    ics = rf.ics_invite(v, to) if v.get("exposure") == "HIGH" else None
    st.session_state.pop(f"jira-{name}", None)
    st.session_state.pop(f"sent-{name}", None)
    st.session_state[f"to-{name}"] = to
    if rf.jira_configured() and unlocked():
        try:
            k, url, how = rf.jira_upsert(v, opt)
            st.session_state[f"jira-{name}"] = k
            log.append(("Jira", f"{how} [{k}]({url})"))
        except ra.AuditError as e:
            log.append(("Jira", f"failed: {e}"))
    else:
        log.append(("Jira", "card ready (preview)"))
    if rf.smtp_configured() and unlocked() and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to or ""):
        try:
            att = [(f"{v.get('module')}_{v.get('assessment')}_revised.txt", revised.encode(), "text/plain")]
            if ics:
                att.append(("redpen-review.ics", ics.encode(), "text/calendar"))
            rf.send_email(to, rf.email_subject(v), rf.email_body(v, red, opt), att, invite=ics)
            st.session_state[f"sent-{name}"] = True
            log.append(("Email", f"**sent** to {to}"))
        except Exception as e:  # noqa: BLE001
            log.append(("Email", f"failed: {e}"))
    elif rf.smtp_configured() and unlocked():
        log.append(("Email", "not sent: add an email address"))
    else:
        log.append(("Email", "ready (preview)"))
    if ics:
        when = f"{rf.next_working_day_10am():%a %d %b, 10:00}"
        log.append(("Calendar", f"**invite sent** for {when}" if st.session_state.get(f"sent-{name}") else f"review set for {when}"))
    st.session_state[f"done-{name}"] = log


def show_done(cur, red, opt):
    v, name = cur["result"]["verdict"], cur["name"]
    to = st.session_state.get(f"to-{name}", "")
    st.divider()
    ui('<div class="rp-h" style="margin-top:0">Done</div>' +
       "".join(f'<div class="rp-check"><i>✓</i><span><b>{esc(w)}:</b> {md_inline(m)}</span></div>'
               for w, m in st.session_state[f"done-{name}"]))
    key = st.session_state.get(f"jira-{name}")
    ics = rf.ics_invite(v, to) if v.get("exposure") == "HIGH" else None
    st.write("")
    with st.container(horizontal=True, gap="small"):
        if key:
            try:
                st.link_button(f"Open {key} in Jira", rf.jira_issue(key)["url"], icon=":material/open_in_new:")
            except ra.AuditError:
                pass
        if ics:
            st.link_button("Add to Google Calendar", rf.google_calendar_link(v, to), icon=":material/event:")
    base = f"{v.get('module')}_{v.get('assessment')}"
    revised = rf.revised_brief(brief_of(cur), v, opt)
    atts = [(f"{base}_revised.txt", revised.encode(), "text/plain")]
    if ics:
        atts.append(("redpen-review.ics", ics.encode(), "text/calendar"))
    st.write("")
    with st.expander("The email", icon=":material/mail:"):
        ui(f'<p><b>{esc(rf.email_subject(v))}</b></p><div class="rp-pre">{pre(rf.email_body(v, red, opt))}</div>')
    with st.expander("Files", icon=":material/download:"):
        with st.container(horizontal=True, gap="small"):
            st.download_button("Revised brief", revised, f"{base}_revised.txt", key=f"rev-{name}")
            st.download_button("Email (.eml)", rf.email_eml(to, rf.email_subject(v), rf.email_body(v, red, opt), atts),
                               f"{base}_redpen-report.eml", mime="message/rfc822", key=f"eml-{name}")
            if ics:
                st.download_button("Invite (.ics)", ics, "redpen-review.ics", mime="text/calendar", key=f"ics-{name}")


def report(cur):
    banner(cur["result"]["verdict"])
    if st.session_state.get("step") not in STEPS:
        st.session_state.step = STEPS[0]
    st.segmented_control("Step", STEPS, key="step", label_visibility="collapsed")
    st.write("")
    s = st.session_state.get("step") or STEPS[0]
    if s == STEPS[0]:
        step_verdict(cur)
    elif s == STEPS[1]:
        step_fix(cur)
    else:
        step_approve(cur)


def page_audit():
    src = st.segmented_control("Source", ["Past audits", "New audit"], default="Past audits", key="src",
                               label_visibility="collapsed", on_change=reset_step)
    if src == "New audit":
        if not unlocked():
            st.info("Enter the judge access code in the sidebar to run a live audit.", icon=":material/lock:")
            return
        live = st.session_state.get("live")
        if not live:
            c1, c2 = st.columns(2)
            module = c1.text_input("Module code", placeholder="CT074-3-2")
            assessment = c2.text_input("Assessment", placeholder="A1")
            c1, c2, c3 = st.columns(3)
            brief_f = c1.file_uploader("Brief", type=["pdf", "docx", "txt", "md"])
            rubric_f = c2.file_uploader("Rubric", type=["pdf", "docx", "txt", "md"])
            clo_f = c3.file_uploader("Learning outcomes", type=["pdf", "docx", "txt", "md"])
            if st.button("Run the red team", type="primary", icon=":material/play_arrow:", disabled=not (brief_f and rubric_f)):
                brief, rubric = read_upload(brief_f), read_upload(rubric_f)
                clo = read_upload(clo_f) or "(no CLO map given)"
                mod, ass = (module or "MODULE").strip().upper(), (assessment or "A1").strip().upper()
                with st.status("Auditing…", expanded=True) as status:
                    def on_step(n, d, secs):
                        status.write(f"{ra.STEP_TITLES.get(n, n)} · {secs:.0f}s")
                    try:
                        res = ra.run_audit(brief, rubric, clo, mod, ass, on_step=on_step)
                    except ra.AuditError as e:
                        status.update(label="Audit failed", state="error")
                        st.error(str(e))
                        return
                    status.update(label="Done", state="complete", expanded=False)
                st.session_state.live = {"result": res, "brief": brief,
                                         "name": f"live-{mod}-{ass}-{dt.datetime.now():%H%M%S}"}
                reset_step()
                st.rerun()
            return
        if st.button("New audit", icon=":material/add:"):
            st.session_state.pop("live", None)
            st.rerun()
        report(live)
        return
    order = sorted(ra.demo_runs(), key=lambda n: (n not in PILOT, n))
    name = st.selectbox("Assessment", order, format_func=past_label, label_visibility="collapsed", on_change=reset_step)
    report({"result": ra.load_demo(name), "name": name})


# ------------------------------------------------------------------ register
def page_register():
    ui('<div class="rp-title">Exposure register</div>')
    order = sorted(ra.demo_runs(), key=lambda n: (n not in PILOT, n))
    rows = []
    for n in order:
        v = ra.load_demo(n)["verdict"]
        rows.append({"Assessment": f"{v.get('module')} {v.get('assessment')}", "Module": v.get("module_name", ""),
                     "Brief": "Real APU" if n in PILOT else "Sample", "Exposure": v.get("exposure"),
                     "Copy-paster": f"{v['persona_grades'].get('copy_paster')} ({v['persona_totals'].get('copy_paster')}%)",
                     "CLOs at risk": ", ".join(c.get("id", "") for c in v.get("clos_at_risk", [])) or "–"})
    real = [ra.load_demo(n)["verdict"] for n in order if n in PILOT]
    real_pass = sum(1 for v in real if v["persona_totals"].get("copy_paster", 0) >= v.get("pass_mark", 50))
    ui('<div class="rp-stats">'
       f'<div class="rp-stat"><b>{len(rows)}</b><span>audited</span></div>'
       f'<div class="rp-stat"><b>{sum(r["Exposure"] == "HIGH" for r in rows)}</b><span>high exposure</span></div>'
       f'<div class="rp-stat"><b>{real_pass} of {len(real)}</b><span>real APU briefs passed by copy-paste</span></div></div>')
    st.dataframe(rows, hide_index=True, width="stretch")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    st.download_button("Download CSV", buf.getvalue(), "redpen-register.csv", mime="text/csv", icon=":material/download:")

    if rf.jira_configured():
        ui('<div class="rp-h">Live from Jira</div>')
        try:
            st.dataframe(rf.jira_register(), hide_index=True, width="stretch")
        except ra.AuditError as e:
            st.warning(f"Jira not reachable: {e}")

    import reaudit
    hist = reaudit.load_history()["runs"]
    last = hist[-1] if hist else None
    last_txt = dt.date.fromisoformat(last["date"][:10]).strftime("%d %b") if last else "–"
    ui('<div class="rp-h">Monthly re-audit</div><div class="rp-stats">'
       '<div class="rp-stat"><b>1st, 09:00</b><span>every month</span></div>'
       f'<div class="rp-stat"><b>{reaudit.next_run():%d %b}</b><span>next run</span></div>'
       f'<div class="rp-stat"><b>{last_txt}</b><span>last run</span></div></div>')
    if last:
        st.dataframe([{"Assessment": r.get("assessment", r["name"]), "Before": r["previous"], "Now": r.get("exposure") or "failed",
                       "Jira": r.get("jira", "–")} for r in last["results"]], hide_index=True, width="stretch")
    st.link_button("Schedule on GitHub Actions", "https://github.com/L0adn9/redPen/actions/workflows/monthly-reaudit.yml",
                   icon=":material/open_in_new:")


# ------------------------------------------------------------------ how it works
def page_how():
    ui('<div class="rp-title">How RedPen works</div>'
       '<div class="rp-flow">'
       '<div><em>1</em><b>Intake</b><p>Reads the brief, the rubric and the learning outcomes.</p></div>'
       '<div><em>2</em><b>Three AI students</b><p>Attempt the assignment, each in a different way.</p></div>'
       '<div><em>3</em><b>Examiner</b><p>Marks every attempt on the real rubric, like a lecturer.</p></div>'
       '<div><em>4</em><b>Verdict</b><p>HIGH, MEDIUM or LOW exposure, and the learning outcomes at risk.</p></div>'
       '<div><em>5</em><b>Redesign</b><p>Fixes that test the same outcomes but are harder to fake.</p></div>'
       '<div><em>6</em><b>Lecturer approves</b><p>Then Jira, Gmail and Calendar do the follow-up.</p></div></div>')
    ui('<div class="rp-h">The three AI students</div>' +
       "".join(f'<div class="rp-clo"><b style="min-width:9rem;color:var(--fg)">{PERSONAS[p]}</b><span>{PERSONA_HELP[p]}</span></div>'
               for p in PERSONAS))
    ui('<div class="rp-h">What the verdict means</div>'
       '<div class="rp-clo"><b style="min-width:6rem">HIGH</b><span>The copy-paster passes.</span></div>'
       '<div class="rp-clo"><b style="min-width:6rem;color:#c08a1e">MEDIUM</b><span>Only the prompt engineer passes.</span></div>'
       '<div class="rp-clo"><b style="min-width:6rem;color:#3c7a4a">LOW</b><span>No AI student passes.</span></div>')
    ui('<div class="rp-h">Can you trust the examiner?</div>'
       '<div class="rp-stats"><div class="rp-stat"><b>7 / 7</b><span>real assignments within one grade band</span></div>'
       '<div class="rp-stat"><b>4.4</b><span>average gap in points</span></div>'
       '<div class="rp-stat"><b>0</b><span>student work read</span></div></div>')
    ui('<div class="rp-h">Built for Gemini Enterprise</div>'
       '<p style="color:var(--fg2);font-size:1rem;line-height:1.6">The same agent instructions run in Gemini Enterprise '
       'workflows: an Audit workflow triggered from Google Drive, a Fix workflow with an approval step and Jira, Gmail and '
       'Calendar actions, and a chat agent over the register.</p>')


# ------------------------------------------------------------------ route
{"Audit": page_audit, "Register": page_register, "How it works": page_how}[page]()
