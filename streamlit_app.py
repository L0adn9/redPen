"""RedPen prototype app (Streamlit).

Run locally:  streamlit run streamlit_app.py
Hosted:       Streamlit Community Cloud, main file streamlit_app.py, secrets as in docs/api-keys.md.

The agents are the prompts in agents/ (the same text pasted into Gemini Enterprise for the final build).
UI: shadcn/ui-style look (zinc palette, Inter, cards, badges) done with CSS on top of Streamlit.
"""
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

PERSONA_NAMES = {"copy_paster": "Copy-paster", "prompt_engineer": "Prompt engineer", "honest_helper": "Honest helper"}
PERSONA_HELP = {"copy_paster": "Pastes the brief into a chatbot and submits the answer as is.",
                "prompt_engineer": "Plans, drafts and self-critiques with AI.",
                "honest_helper": "Uses AI only the way the brief allows."}
PILOT = {"CCP_A1", "DSTR_LW1", "DSTR_LW2", "WAPP_GA"}
TONE = {"HIGH": "red", "MEDIUM": "amber", "LOW": "green"}

# ------------------------------------------------------------------ styles (shadcn/ui look)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Geist:wght@400;500;600;700&display=swap');
:root{--bg:#fcf9f2;--fg:#231b14;--fg2:#4a4039;--card:#fffdfa;--muted:#71675d;--border:#e3ddd3;--input:#c9bfb1;--subtle:#f3eee4;
  --primary:#b65329;--primary-fg:#fffdfa;--radius:14px;--shadow:0 1px 3px rgba(35,27,20,.07),0 1px 2px -1px rgba(35,27,20,.07);
  --serif:'Fraunces',Georgia,serif;--sans:'Geist',ui-sans-serif,system-ui,sans-serif}
html,body,[class*="st-"],.stMarkdown,button,input,textarea,select{font-family:var(--sans)!important}
[data-testid="stIconMaterial"],[data-testid="stExpanderIcon"],.material-symbols-rounded{font-family:'Material Symbols Rounded'!important}
.stApp{background:radial-gradient(1000px 480px at 50% -120px,rgba(182,83,41,.09),transparent 70%),var(--bg)!important}
/* top spacing: main */
header[data-testid="stHeader"]{background:transparent!important;height:2.5rem}
[data-testid="stMainBlockContainer"],.block-container{max-width:1080px;padding-top:.2rem!important;padding-bottom:3rem}
/* sidebar: collapse button sits on the brand row (top-right) instead of pushing the brand down */
[data-testid="stSidebar"]{background:#f6f1e7!important;border-right:1px solid var(--border)}
[data-testid="stSidebarHeader"]{position:absolute!important;top:1.15rem;right:.6rem;height:auto!important;min-height:0!important;
  padding:0!important;margin:0!important;z-index:5;width:auto!important}
[data-testid="stSidebarUserContent"]{padding-top:1.25rem!important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.85rem}
#MainMenu,footer,[data-testid="stDecoration"]{display:none!important}
h1,h2,h3,h4{color:var(--fg);font-family:var(--serif)!important;letter-spacing:-.02em}
/* inputs: always a clearly visible border */
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{
  background:#fff!important;border:1px solid var(--input)!important;border-radius:10px!important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within,[data-baseweb="textarea"]:focus-within{
  border-color:var(--primary)!important;box-shadow:0 0 0 3px rgba(182,83,41,.15)!important}
[data-baseweb="input"] input,[data-baseweb="base-input"],[data-baseweb="input"] button{background:transparent!important;border:none!important}
[data-testid="InputInstructions"]{display:none!important}
[data-testid="stWidgetLabel"] p{font-size:.875rem!important;font-weight:500!important;color:var(--fg)!important}
/* buttons: terracotta pill primary, outline secondary */
.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:999px!important;font-weight:500!important;font-size:.9rem!important;
  min-height:2.5rem;border:1px solid var(--input)!important;background:#fff!important;color:var(--fg)!important;box-shadow:var(--shadow)}
.stButton>button[kind="primary"]{background:var(--primary)!important;color:var(--primary-fg)!important;border-color:var(--primary)!important}
.stButton>button[kind="primary"]:hover{filter:brightness(1.08)}
.stButton>button[kind="secondary"]:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{background:var(--subtle)!important;
  border-color:#b3a898!important;color:var(--fg)!important}
/* containers, expanders, tables */
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:var(--radius)!important;border-color:var(--border)!important}
[class*="st-key-rpbox"]{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:var(--radius)!important;
  box-shadow:var(--shadow);padding:1.1rem 1.2rem!important;gap:.75rem}
[data-testid="stExpander"] details{border-radius:12px!important;border-color:var(--border)!important;background:var(--card)}
[data-testid="stExpander"] summary{font-weight:500;font-size:.9rem}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:12px;overflow:hidden;background:#fff}
hr{margin:1.6rem 0!important;border-color:var(--border)!important}
/* components */
.rp-hero{margin:0 0 1.3rem 0}
.rp-hero h1{font-family:var(--serif)!important;font-size:2.5rem;font-weight:600;letter-spacing:-.025em;margin:.7rem 0 .35rem 0;padding:0;line-height:1.1}
.rp-hero p{color:var(--muted);font-size:1.02rem;margin:0;max-width:760px;line-height:1.55}
.rp-muted{color:var(--muted);font-size:.875rem;line-height:1.5}
.rp-lead{color:var(--fg2);font-size:.95rem;line-height:1.55}
.rp-badge{display:inline-flex;align-items:center;gap:.3rem;border:1px solid var(--border);border-radius:999px;padding:.08rem .6rem;
  font-size:.74rem;font-weight:500;line-height:1.35rem;background:var(--subtle);color:var(--fg2);white-space:nowrap}
.rp-badge.solid{background:var(--primary);color:var(--primary-fg);border-color:var(--primary);font-weight:600}
.rp-badge.red{background:#fef2f2;color:#b91c1c;border-color:#fecaca}
.rp-badge.amber{background:#fffbeb;color:#b45309;border-color:#fde68a}
.rp-badge.green{background:#f0fdf4;color:#15803d;border-color:#bbf7d0}
.rp-badge.gray{background:var(--subtle);color:var(--fg2)}
.rp-badge.lg{font-size:.82rem;padding:.2rem .75rem;font-weight:600}
.rp-step{display:flex;gap:.85rem;align-items:flex-start;margin:1.9rem 0 .85rem 0}
.rp-step-n{flex:none;width:2rem;height:2rem;border-radius:999px;background:rgba(182,83,41,.09);color:var(--primary);
  border:1px solid rgba(182,83,41,.3);display:flex;align-items:center;justify-content:center;font-weight:600;font-size:.85rem;margin-top:.15rem}
.rp-step-t{font-family:var(--serif);font-weight:600;font-size:1.45rem;letter-spacing:-.015em;line-height:1.25;color:var(--fg)}
.rp-card{border:1px solid var(--border);border-radius:var(--radius);padding:1.05rem 1.15rem;background:var(--card);box-shadow:var(--shadow);height:100%}
.rp-card.tint-red{background:linear-gradient(180deg,#fef4f2,var(--card));border-color:#f5c9c0}
.rp-card.tint-amber{background:linear-gradient(180deg,#fff8eb,var(--card));border-color:#f3dca6}
.rp-card.tint-green{background:linear-gradient(180deg,#f2fbf3,var(--card));border-color:#c4e8cb}
.rp-row{display:flex;justify-content:space-between;align-items:center;gap:.6rem}
.rp-grid{display:grid;gap:.75rem;margin:.75rem 0}
.rp-g3{grid-template-columns:repeat(3,minmax(0,1fr))}.rp-g2{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:760px){.rp-g3,.rp-g2{grid-template-columns:1fr}}
.rp-label{font-size:.875rem;font-weight:600;color:var(--fg)}
.rp-grade{font-family:var(--serif);font-size:2.2rem;font-weight:600;letter-spacing:-.03em;margin:.3rem 0 .1rem 0;color:var(--fg)}
.rp-grade span{font-family:var(--sans);font-size:1rem;font-weight:500;color:var(--muted);margin-left:.4rem}
.rp-bar{position:relative;height:.4rem;border-radius:999px;background:var(--subtle);margin:.6rem 0 .55rem 0}
.rp-bar>i{position:absolute;left:0;top:0;bottom:0;border-radius:999px;background:var(--primary)}
.rp-bar>b{position:absolute;top:-.28rem;bottom:-.28rem;width:2px;background:#dc2626;border-radius:2px}
.rp-title{font-family:var(--serif);font-size:1.6rem;font-weight:600;letter-spacing:-.02em;margin:.55rem 0 .3rem 0;color:var(--fg)}
.rp-meta{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.75rem}
.rp-alert{border:1px solid #f5c9c0;background:#fef4f2;border-radius:12px;padding:.8rem 1rem;margin:.5rem 0;color:#8a2a17}
.rp-alert.ok{border-color:#c4e8cb;background:#f2fbf3;color:#14532d}
.rp-alert b{display:block;margin-bottom:.15rem;color:inherit}
.rp-alert .rp-muted{color:inherit;opacity:.85}
.rp-section-label{font-size:.74rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:1.2rem 0 .25rem 0}
.rp-stat{font-family:var(--serif);font-size:1.75rem;font-weight:600;letter-spacing:-.02em;margin-top:.15rem;color:var(--fg)}
.rp-pre{white-space:pre-wrap;font-size:.875rem;line-height:1.6;background:#fff;border:1px solid var(--border);
  border-radius:12px;padding:.9rem 1rem;max-height:340px;overflow:auto;color:var(--fg2)}
.rp-pre.plain{background:transparent;border:none;padding:0;max-height:none;overflow:visible;margin-bottom:.4rem}
.rp-check{display:flex;gap:.55rem;align-items:flex-start;margin:.4rem 0;font-size:.9rem;color:var(--fg2)}
.rp-check b{color:var(--fg)}
.rp-check a{color:var(--primary)}
.rp-check>span:first-child{flex:none;width:1.15rem;height:1.15rem;border-radius:999px;background:var(--primary);color:var(--primary-fg);
  font-size:.68rem;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:.15rem}
.rp-mail-h{display:grid;grid-template-columns:5.5rem 1fr;gap:.3rem .5rem;font-size:.875rem;padding-bottom:.75rem;
  border-bottom:1px solid var(--border);margin-bottom:.75rem;color:var(--fg2)}
.rp-mail-h>div:nth-child(odd){color:var(--muted)}
.rp-date{flex:none;width:3.6rem;border:1px solid var(--border);border-radius:10px;overflow:hidden;text-align:center;background:#fff}
.rp-date>div:first-child{background:var(--primary);color:var(--primary-fg);font-size:.7rem;font-weight:700;padding:.12rem 0;text-transform:uppercase}
.rp-date>div:last-child{font-family:var(--serif);font-size:1.4rem;font-weight:600;padding:.2rem 0;color:var(--fg)}
.rp-brand{display:flex;align-items:center;gap:.6rem;margin:0 0 .15rem 0;min-height:2rem}
.rp-logo{width:2rem;height:2rem;border-radius:9px;background:var(--primary);display:flex;align-items:center;justify-content:center;font-size:1rem}
.rp-brand span{font-family:var(--serif);font-size:1.3rem;font-weight:600;letter-spacing:-.01em;color:var(--fg)}
.rp-flow{font-size:.8rem;color:var(--muted);line-height:1.95}
.rp-flow b{color:var(--fg);font-weight:500}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{font-size:.82rem!important}
[data-testid="stSidebar"] hr{margin:.3rem 0!important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p{font-size:.85rem!important}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def esc(x):
    return html.escape(str(x if x is not None else ""))


def pre(x):
    """Escaped multi-line text as ONE html block (no blank lines, so Streamlit's markdown never re-parses it)."""
    return esc(x).replace("\r", "").replace("\n", "<br>")


def human(x):
    """Readable persona names inside model-written sentences."""
    for k, n in (("copy_paster", "copy-paster"), ("prompt_engineer", "prompt engineer"), ("honest_helper", "honest helper")):
        x = str(x).replace(k, n)
    return x


def md_inline(x):
    """**bold** and [text](url) from the action log -> html."""
    import re
    x = esc(x)
    x = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", x)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank">\1</a>', x)


def ui(markup):
    st.markdown(markup, unsafe_allow_html=True)


def badge(text, tone="", size=""):
    return f'<span class="rp-badge {tone} {size}">{esc(text)}</span>'


def step(n, title, sub):
    ui(f'<div class="rp-step"><div class="rp-step-n">{n}</div><div><div class="rp-step-t">{esc(title)}</div>'
       f'<div class="rp-muted">{esc(sub)}</div></div></div>')


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


def unlocked():
    pw = os.environ.get("APP_PASSWORD", "")
    return not pw or st.session_state.get("pw_ok", False)


# ------------------------------------------------------------------ 1 · audit
def show_verdict(result, is_real=None):
    v, steps = result["verdict"], result["steps"]
    exp = v.get("exposure", "?")
    tone = TONE.get(exp, "gray")
    tags = [badge(f"{exp} AI-exposure", tone, "lg")]
    if is_real is not None:
        tags.append(badge("Real APU brief" if is_real else "Sample brief", "gray"))
    meta = [badge(f"Pass mark {v.get('pass_mark')}%"), badge(f"Audited {v.get('audit_date')}"),
            badge(f"Gemini {v.get('model')}")]
    ui(f'<div class="rp-card tint-{tone}"><div class="rp-row" style="justify-content:flex-start;gap:.4rem">{"".join(tags)}</div>'
       f'<div class="rp-title">{esc(v.get("module"))} {esc(v.get("assessment"))} · {esc(v.get("module_name", ""))}</div>'
       f'<div class="rp-lead">{esc(human(v.get("summary", "")))}</div>'
       f'<div class="rp-meta">{"".join(meta)}</div></div>')

    cards = []
    pass_mark = v.get("pass_mark", 50) or 50
    for p, label in PERSONA_NAMES.items():
        total = v.get("persona_totals", {}).get(p) or 0
        grade = v.get("persona_grades", {}).get(p, "-")
        passed = total >= pass_mark
        state = badge("Passes", "red" if p != "honest_helper" else "gray") if passed else badge("Fails", "green" if p != "honest_helper" else "gray")
        cards.append(f'<div class="rp-card"><div class="rp-row"><span class="rp-label">{label}</span>{state}</div>'
                     f'<div class="rp-grade">{esc(grade)}<span>{total}%</span></div>'
                     f'<div class="rp-bar"><i style="width:{min(total, 100)}%"></i><b style="left:{pass_mark}%"></b></div>'
                     f'<div class="rp-muted">{PERSONA_HELP[p]}</div></div>')
    ui(f'<div class="rp-grid rp-g3">{"".join(cards)}</div>'
       f'<div class="rp-muted" style="font-size:.78rem;margin-top:.15rem">Red tick on each bar = pass mark.</div>')

    if v.get("clos_at_risk"):
        ui('<div class="rp-section-label">Learning outcomes this assessment no longer reliably proves</div>')
        ui("".join(f'<div class="rp-alert"><b>{esc(c.get("id"))} · {esc(c.get("text"))}</b>'
                   f'<div class="rp-muted">{esc(human(c.get("why", "")))}</div></div>' for c in v["clos_at_risk"]))
    else:
        ui('<div class="rp-alert ok"><b>No learning outcomes at risk</b><div class="rp-muted">The AI students could not pass.</div></div>')
    if v.get("easy_criteria"):
        ui('<div class="rp-section-label">Rubric criteria the AI met easily</div>'
           f'<div class="rp-meta" style="margin-top:.4rem">{"".join(badge(c) for c in v["easy_criteria"])}</div>')

    st.write("")
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


# ------------------------------------------------------------------ 2 · fix, 3 · approve
def show_fix(result, brief_text, name):
    v = result["verdict"]
    if v.get("exposure") not in ("HIGH", "MEDIUM"):
        ui('<div class="rp-alert ok" style="margin-top:1.2rem"><b>LOW exposure: no redesign needed</b>'
           '<div class="rp-muted">It is still logged in the register and re-audited monthly.</div></div>')
        return
    step(2, "Fix", "Redesign options that keep testing the same learning outcomes but make AI-only completion fail.")
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
    if red.get("why_recommended"):
        ui(f'<div class="rp-lead" style="margin-bottom:.6rem">{esc(red["why_recommended"])}</div>')
    ids = [o.get("id") for o in opts]
    pick = st.radio("Choose a redesign", ids, index=ids.index(red.get("recommended")) if red.get("recommended") in ids else 0,
                    format_func=lambda i: next(f"{o['id']}: {o.get('title')}" + (" (recommended)" if i == red.get("recommended") else "")
                                               for o in opts if o["id"] == i), horizontal=True)
    opt = rf.option(red, pick)
    stats = [("AIAS level", opt.get("aias_level")), ("Lane", str(opt.get("lane", "")).title()),
             ("Extra marking / student", f"{opt.get('extra_marking_minutes_per_student')} min")]
    ui('<div class="rp-grid rp-g3">' + "".join(f'<div class="rp-card"><div class="rp-muted">{a}</div><div class="rp-stat">{esc(b)}</div></div>'
                                              for a, b in stats) + '</div>')
    if opt.get("techniques"):
        ui('<div class="rp-section-label">Techniques</div>'
           f'<div class="rp-meta" style="margin-top:.4rem">{"".join(badge(t) for t in opt["techniques"])}</div>')
    if opt.get("clo_coverage"):
        ui('<div class="rp-section-label">Same learning outcomes, still assessed</div>' +
           "".join(f'<div class="rp-check"><span>✓</span><span><b>{esc(c.get("id"))}</b> · {esc(c.get("how"))}</span></div>'
                   for c in opt["clo_coverage"]))
    ui('<div class="rp-section-label">Revised task text</div>'
       f'<div class="rp-pre">{pre(opt.get("revised_task_text", ""))}</div>')

    step(3, "Lecturer approval", "Human in the loop: nothing is changed, logged or sent until the lecturer approves.")
    with st.container(border=True, key=f"rpbox-approve-{name}"):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        to = c1.text_input("Lecturer email", value=v.get("lecturer_email", "") if "@" in v.get("lecturer_email", "") and
                           "REPLACE" not in v.get("lecturer_email", "") else os.environ.get("DEMO_LECTURER_EMAIL", ""),
                           placeholder="lecturer@university.edu.my",
                           help="With the judge password, RedPen really emails this address (the report, the revised brief "
                                "and, for HIGH exposure, a calendar invitation). Use your own email to see it arrive.")
        approve = c2.button(f"Approve {pick}  →", type="primary", width="stretch")
        if not unlocked():
            ui('<div class="rp-muted" style="font-size:.8rem;margin:-.15rem 0 .1rem 0">🔒 Approve works for everyone and shows every follow-up below. '
               'Writing the real Jira card and emailing the lecturer need the judge password (sidebar).</div>')
    if approve:
        do_actions(v, red, opt, brief_text, to, name)
    if st.session_state.get(f"done-{name}"):
        show_downloads(v, red, opt, brief_text, name)


def do_actions(v, red, opt, brief_text, to, name):
    log = []
    revised = rf.revised_brief(brief_text, v, opt)
    ics = rf.ics_invite(v, to) if v.get("exposure") == "HIGH" else None
    st.session_state.pop(f"jira-{name}", None)
    if rf.jira_configured() and unlocked():
        try:
            k, url, how = rf.jira_upsert(v, opt)
            st.session_state[f"jira-{name}"] = k
            log.append(("Jira", f"{how} [{k}]({url}) in the Assessment Exposure Register, labels {', '.join(rf.jira_labels(v))}"))
        except ra.AuditError as e:
            log.append(("Jira", f"⚠️ {e}"))
    elif rf.jira_configured():
        log.append(("Jira", "preview only (enter the judge password in the sidebar to write the real card). Card: "
                            f"**{v.get('module')} {v.get('assessment')}**, labels {', '.join(rf.jira_labels(v))}"))
    else:
        log.append(("Jira", "not configured here (set JIRA_* secrets). Card that would be created: "
                            f"**{v.get('module')} {v.get('assessment')}**, labels {', '.join(rf.jira_labels(v))}"))
    st.session_state[f"to-{name}"] = to
    st.session_state.pop(f"sent-{name}", None)
    if rf.smtp_configured() and unlocked() and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", to or ""):
        try:
            att = [(f"{v.get('module')}_{v.get('assessment')}_revised.txt", revised.encode(), "text/plain")]
            if ics:
                att.append(("redpen-review.ics", ics.encode(), "text/calendar"))
            rf.send_email(to, rf.email_subject(v), rf.email_body(v, red, opt), att, invite=ics)
            st.session_state[f"sent-{name}"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%H:%M")
            log.append(("Email", f"**sent via Gmail** to {to}: report + revised brief" +
                        (" + a calendar invitation" if ics else "") + ". Check the inbox."))
        except Exception as e:  # noqa: BLE001
            log.append(("Email", f"⚠️ {e}"))
    elif rf.smtp_configured() and unlocked():
        log.append(("Email", "not sent: type a lecturer email above (your own works) and approve again. Preview below."))
    else:
        log.append(("Email", "ready in the outbox below: read it on screen or download it (.eml opens in any mail app). "
                             "With the judge password it is sent for real via Gmail."))
    if ics:
        when = f"{rf.next_working_day_10am():%a %d %b, 10:00} MYT"
        log.append(("Calendar", f"**invitation sent**: 30-min T&L review on {when}; Gmail adds it to Google Calendar"
                    if st.session_state.get(f"sent-{name}") else f"30-min T&L review for {when} (in the outbox below)"))
    log.append(("Revised brief", "ready to download below"))
    st.session_state[f"done-{name}"] = log


def show_reaudit():
    """The scheduled half of RedPen Audit: monthly re-audit results (data/reaudit/history.json, written by
    tools/reaudit.py from the GitHub Actions schedule)."""
    import reaudit
    st.divider()
    step("↻", "Monthly re-audit (scheduled)",
         "Every stronger model can make last month's safe assessment unsafe. On the 1st of every month at 09:00 MYT, "
         "RedPen re-runs the red team on every assessment in the register, comments the result on each Jira card and "
         "emails an alert if exposure went up. No one presses a button.")
    hist = reaudit.load_history()["runs"]
    last = hist[-1] if hist else None
    nxt = reaudit.next_run()
    cards = [("Schedule", "1st of month, 09:00"), ("Next run", f"{nxt:%d %b %Y}"),
             ("Last run", f"{last['date']} ({'scheduled' if last['trigger'] == 'schedule' else 'manual'})" if last else "not yet")]
    ui('<div class="rp-grid rp-g3">' + "".join(
        f'<div class="rp-card"><div class="rp-muted">{a}</div><div class="rp-stat" style="font-size:1.25rem">{esc(b)}</div></div>'
        for a, b in cards) + '</div>')
    if last:
        arrow = {"same": "= no change", "up": "▲ went up", "down": "▼ went down"}
        rows = [{"Assessment": r.get("assessment", r["name"]), "Last audit": f"{r['previous']} ({r.get('previous_date', '')})",
                 "This run": r.get("exposure") or "failed", "Change": arrow.get(r.get("change"), "-"),
                 "Copy-paster": f"{r.get('totals', {}).get('copy_paster', '-')}%", "Jira": r.get("jira", "-"),
                 "Model": r.get("model", "-")} for r in last["results"]]
        st.dataframe(rows, hide_index=True, width="stretch")
    st.link_button("See the schedule and its runs on GitHub Actions ↗",
                   "https://github.com/L0adn9/redPen/actions/workflows/monthly-reaudit.yml")


def show_downloads(v, red, opt, brief_text, name):
    with st.container(border=True, key=f"rpbox-done-{name}"):
        ui('<div class="rp-row" style="justify-content:flex-start;gap:.5rem;margin-bottom:.3rem">'
           f'{badge("Approved", "green", "lg")}<span class="rp-label">RedPen did the follow-up</span></div>')
        ui("".join(f'<div class="rp-check"><span>✓</span><span><b>{esc(what)}:</b> {md_inline(msg)}</span></div>'
                   for what, msg in st.session_state[f"done-{name}"]))
    base = f"{v.get('module')}_{v.get('assessment')}"
    to = st.session_state.get(f"to-{name}", "")
    revised = rf.revised_brief(brief_text, v, opt)
    ics = rf.ics_invite(v, to) if v.get("exposure") == "HIGH" else None

    step("✉", "Outbox", "Everything RedPen sent, exactly as the lecturer receives it.")
    key = st.session_state.get(f"jira-{name}")
    if key:
        with st.container(border=True, key=f"rpbox-jira-{name}"):
            try:
                i = rf.jira_issue(key)
                ui(f'<div class="rp-row"><span class="rp-label">Jira · Assessment Exposure Register</span>'
                   f'{badge("Read back live from Jira", "gray")}</div>'
                   f'<div class="rp-row" style="justify-content:flex-start;gap:.5rem;margin:.7rem 0 .3rem 0">'
                   f'{badge(i["key"], "solid", "lg")}{badge(i["status"], "green", "lg")}'
                   f'<span style="font-weight:600">{esc(i["summary"])}</span></div>'
                   f'<div class="rp-meta">{"".join(badge(lb) for lb in i["labels"])}</div>'
                   f'<div class="rp-muted" style="margin:.55rem 0 1rem 0;font-size:.8rem">Updated {esc(i["updated"])}</div>')
                st.link_button("Open the card in Jira ↗", i["url"])
            except ra.AuditError as e:
                st.warning(f"Could not read the card back: {e}")

    atts = [(f"{base}_revised.txt", revised.encode(), "text/plain")]
    if ics:
        atts.append(("redpen-review.ics", ics.encode(), "text/calendar"))
    with st.container(border=True, key=f"rpbox-mail-{name}"):
        ui('<div class="rp-row" style="margin-bottom:.7rem"><span class="rp-label">Email to the lecturer</span>'
           f'{badge("Sent via Gmail · " + st.session_state[f"sent-{name}"] + " MYT", "green") if st.session_state.get(f"sent-{name}") else badge("Report", "gray")}</div>'
           '<div class="rp-mail-h">'
           f'<div>From</div><div>RedPen</div><div>To</div><div>{esc(to or "(lecturer email)")}</div>'
           f'<div>Subject</div><div style="font-weight:600">{esc(rf.email_subject(v))}</div>'
           f'<div>Attached</div><div>{"".join(badge("📎 " + a[0]) + " " for a in atts)}</div></div>'
           f'<div class="rp-pre plain">{pre(rf.email_body(v, red, opt))}</div>')
        st.download_button("Download this email (.eml)", rf.email_eml(to, rf.email_subject(v), rf.email_body(v, red, opt), atts),
                           f"{base}_redpen-report.eml", mime="message/rfc822", key=f"eml-{name}")

    if ics:
        e = rf.calendar_event(v, to)
        with st.container(border=True, key=f"rpbox-cal-{name}"):
            ui('<div class="rp-row" style="margin-bottom:.7rem"><span class="rp-label">Calendar · T&amp;L review meeting</span>'
               f'{badge("Booked because exposure is HIGH", "red")}'
               f'{" " + badge("Invitation sent", "green") if st.session_state.get(f"sent-{name}") else ""}</div>'
               f'<div class="rp-row" style="justify-content:flex-start;gap:.9rem">'
               f'<div class="rp-date"><div>{e["start"]:%b}</div><div>{e["start"]:%d}</div></div>'
               f'<div><div style="font-weight:600">{esc(e["title"])}</div>'
               f'<div class="rp-muted">{e["start"]:%A %d %B %Y} · {e["start"]:%H:%M}–{e["end"]:%H:%M} ({e["tz"]}) · 30 min</div>'
               f'<div class="rp-muted">Guests: {esc(", ".join(e["guests"]))}</div></div></div>')
            st.write("")
            c1, c2, _ = st.columns([1, 1, 1])
            c1.link_button("Add to Google Calendar ↗", rf.google_calendar_link(v, to), width="stretch")
            c2.download_button("Download invite (.ics)", ics, "redpen-review.ics", mime="text/calendar", key=f"ics-{name}",
                               width="stretch")

    with st.container(border=True, key=f"rpbox-files-{name}"):
        ui('<div class="rp-label" style="margin-bottom:.6rem">Files</div>')
        c1, c2, _ = st.columns([1, 1, 1])
        c1.download_button("Revised brief (.txt)", revised, f"{base}_revised.txt", key=f"rev-{name}", width="stretch")
        c2.download_button("Verdict (.json)", json.dumps(v, indent=2), f"{base}_verdict.json", mime="application/json",
                           key=f"ver-{name}", width="stretch")
        with st.expander("Preview the revised brief"):
            st.text(revised[:6000])


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    ui('<div class="rp-brand"><div class="rp-logo">🖍️</div><span>RedPen</span></div>'
       '<div class="rp-muted" style="margin-bottom:.9rem">They catch students. We fix assignments.</div>')
    mode = st.radio("Mode", ["Saved audits (instant)", "Run a new audit"], index=0)
    st.divider()
    if os.environ.get("APP_PASSWORD") and not st.session_state.get("pw_ok"):
        pw = st.text_input("Judge password", type="password", help="Unlocks the real Jira write, real email + calendar invitation, and live audits.",
                           placeholder="Enter password")
        ui('<div class="rp-muted" style="font-size:.76rem;margin-top:-.45rem">Press Enter to unlock.</div>')
        if pw:
            st.session_state.pw_ok = pw == os.environ["APP_PASSWORD"]
            if st.session_state.pw_ok:
                st.rerun()  # swap the field for the "Unlocked" badge straight away
            st.error("Wrong password")
    elif os.environ.get("APP_PASSWORD"):
        ui(badge("🔓 Unlocked: real Jira, Gmail + live audits", "green"))
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
    st.divider()
    ui('<div class="rp-section-label" style="margin-top:0">How it works</div><div class="rp-flow">'
       '<b>Intake</b> reads brief, rubric, CLO map<br><b>3 AI students</b> attempt it<br><b>Examiner</b> marks on the real rubric<br>'
       '<b>Verdict</b> exposure + CLOs at risk<br><b>Redesign</b> same CLOs, harder to fake<br><b>Lecturer approves</b><br>'
       '<b>Jira · email · calendar</b></div>'
       '<div class="rp-muted" style="font-size:.78rem;margin-top:.8rem">Same agent prompts as our Gemini Enterprise workflows.</div>')

ui('<div class="rp-hero">' + badge("Prototype · Gemini", "gray") + " " + badge("APU Cloud Innovation Hackathon 2026", "gray") +
   '<h1>An AI red team for your assessments</h1>'
   '<p>Before students get AI to do the assignment, RedPen already has, and tells you which learning outcomes '
   'you can no longer trust. Then it fixes the assignment, with the lecturer.</p></div>')

# ------------------------------------------------------------------ main
if mode.startswith("Saved"):
    runs = ra.demo_runs()
    order = sorted(runs, key=lambda n: (n not in PILOT, n))
    name = st.selectbox("Choose an audited assessment", order, format_func=demo_label)
    result = ra.load_demo(name)
    step(1, "Audit", "Three AI students attempt the assignment; an AI examiner marks them on the real rubric.")
    show_verdict(result, is_real=name in PILOT)
    show_fix(result, rf.brief_for_demo(name, result["steps"].get("01-intake", {})), name)

    st.divider()
    ui('<div class="rp-step" style="margin-top:0"><div class="rp-step-n">≡</div><div><div class="rp-step-t">Assessment Exposure Register</div>'
       '<div class="rp-muted">Every audited assessment, its exposure and the learning outcomes at risk.</div></div></div>')
    rows = []
    for n in order:
        v = ra.load_demo(n)["verdict"]
        rows.append({"Assessment": f"{v.get('module')} {v.get('assessment')}", "Module": v.get("module_name", ""),
                     "Brief": "real APU" if n in PILOT else "sample", "Exposure": v.get("exposure"),
                     "Copy-paster": f"{v['persona_grades'].get('copy_paster')} ({v['persona_totals'].get('copy_paster')}%)",
                     "CLOs at risk": ", ".join(c.get("id", "") for c in v.get("clos_at_risk", [])) or "-"})
    high = sum(r["Exposure"] == "HIGH" for r in rows)
    real_pass = sum(1 for n in order if n in PILOT and
                    ra.load_demo(n)["verdict"]["persona_totals"].get("copy_paster", 0) >= ra.load_demo(n)["verdict"].get("pass_mark", 50))
    ui('<div class="rp-grid rp-g3">' + "".join(
        f'<div class="rp-card"><div class="rp-muted">{a}</div><div class="rp-stat">{b}</div></div>' for a, b in
        [("Assessments audited", len(rows)), ("HIGH exposure", high),
         ("Real APU briefs passed by copy-paste", f"{real_pass} of {len(PILOT)}")]) + '</div>')
    st.dataframe(rows, hide_index=True, width="stretch")
    import csv

    csv_buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(csv_buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    st.download_button("Download CSV", csv_buf.getvalue(), "redpen-register.csv", mime="text/csv")
    if rf.jira_configured():
        ui('<div class="rp-section-label">Live from Jira · RP board</div>')
        try:
            st.dataframe(rf.jira_register(), hide_index=True, width="stretch")
            st.caption("Every lecturer approval creates or updates one card here. The Gemini Enterprise version uses the Jira Cloud connector.")
        except ra.AuditError as e:
            st.caption(f"Jira not reachable right now: {e}")
    show_reaudit()
else:
    if not unlocked():
        st.warning("Enter the judge password in the sidebar to run a live audit (each run uses 6 Gemini calls). "
                   "Saved audits work without it.")
        st.stop()
    step(1, "Audit a new assessment", "Upload a brief and its rubric (PDF, DOCX or TXT). Takes about 1–5 minutes.")
    with st.container(border=True, key=f"rpbox-upload"):
        c1, c2 = st.columns(2)
        module = c1.text_input("Module code", "DEMO101")
        assessment = c2.text_input("Assessment", "A1")
        brief_f = st.file_uploader("Assignment brief", type=["txt", "pdf", "docx", "md"])
        rubric_f = st.file_uploader("Marking rubric", type=["txt", "pdf", "docx", "md"])
        clo_f = st.file_uploader("CLO map (optional)", type=["txt", "pdf", "docx", "md"])
        email = st.text_input("Lecturer email (optional)")
        run = st.button("Run the red team", type="primary", disabled=not (brief_f and rubric_f))
    if run:
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

st.divider()
ui('<div class="rp-muted" style="font-size:.8rem">RedPen is a risk signal from simulated AI attempts marked by an AI examiner '
   '(calibrated: 7 of 7 real assignments within one grade band of independent reference marks). '
   'It never sees or judges real student work.</div>')
