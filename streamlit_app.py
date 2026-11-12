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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--bg:#fff;--fg:#09090b;--muted:#71717a;--border:#e4e4e7;--subtle:#f4f4f5;--soft:#fafafa;--radius:.75rem}
html,body,[class*="st-"],.stMarkdown,button,input,textarea,select{font-family:'Inter',ui-sans-serif,system-ui,sans-serif!important}
[data-testid="stIconMaterial"],[data-testid="stExpanderIcon"],.material-symbols-rounded{font-family:'Material Symbols Rounded'!important}
.block-container{max-width:1080px;padding-top:3rem;padding-bottom:4rem}
#MainMenu,footer{visibility:hidden}
header[data-testid="stHeader"]{background:transparent}
h1,h2,h3,h4{letter-spacing:-.02em;color:var(--fg)}
[data-testid="stSidebar"]{background:var(--soft);border-right:1px solid var(--border)}
[data-testid="stSidebar"] .block-container{padding-top:1.5rem}
/* buttons */
.stButton>button,.stDownloadButton>button,.stLinkButton>a{border-radius:.5rem!important;font-weight:500!important;
  font-size:.875rem!important;min-height:2.35rem;border:1px solid var(--border)!important;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.stButton>button[kind="primary"]{background:#18181b!important;color:#fafafa!important;border-color:#18181b!important}
.stButton>button[kind="primary"]:hover{background:#27272a!important}
.stButton>button[kind="secondary"]:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{background:var(--subtle)!important;
  color:var(--fg)!important;border-color:var(--border)!important}
/* bordered containers, expanders, inputs */
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:var(--radius)!important;border-color:var(--border)!important}
[data-testid="stExpander"] details{border-radius:var(--radius)!important;border-color:var(--border)!important}
[data-testid="stExpander"] summary{font-weight:500;font-size:.9rem}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{border-radius:.5rem!important}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
hr{margin:2rem 0!important;border-color:var(--border)!important}
/* components */
.rp-hero{margin-bottom:1.5rem}
.rp-hero h1{font-size:2.1rem;font-weight:700;margin:.6rem 0 .3rem 0;padding:0}
.rp-hero p{color:var(--muted);font-size:1.02rem;margin:0;max-width:760px}
.rp-muted{color:var(--muted);font-size:.875rem;line-height:1.45}
.rp-badge{display:inline-flex;align-items:center;gap:.3rem;border:1px solid var(--border);border-radius:.4rem;padding:.1rem .5rem;
  font-size:.75rem;font-weight:600;line-height:1.3rem;background:#fff;color:var(--fg);white-space:nowrap}
.rp-badge.solid{background:#18181b;color:#fafafa;border-color:#18181b}
.rp-badge.red{background:#fef2f2;color:#b91c1c;border-color:#fecaca}
.rp-badge.amber{background:#fffbeb;color:#b45309;border-color:#fde68a}
.rp-badge.green{background:#f0fdf4;color:#15803d;border-color:#bbf7d0}
.rp-badge.gray{background:var(--subtle);color:#3f3f46}
.rp-badge.lg{font-size:.85rem;padding:.25rem .7rem}
.rp-step{display:flex;gap:.85rem;align-items:flex-start;margin:2.2rem 0 1rem 0}
.rp-step-n{flex:none;width:1.9rem;height:1.9rem;border-radius:999px;background:#18181b;color:#fafafa;display:flex;align-items:center;
  justify-content:center;font-weight:600;font-size:.85rem;margin-top:.1rem}
.rp-step-t{font-weight:600;font-size:1.2rem;letter-spacing:-.01em}
.rp-card{border:1px solid var(--border);border-radius:var(--radius);padding:1rem 1.1rem;background:#fff;
  box-shadow:0 1px 2px rgba(0,0,0,.04);height:100%}
.rp-card.tint-red{background:#fffafa;border-color:#fecaca}.rp-card.tint-amber{background:#fffdf7;border-color:#fde68a}
.rp-card.tint-green{background:#fbfffc;border-color:#bbf7d0}
.rp-row{display:flex;justify-content:space-between;align-items:center;gap:.6rem}
.rp-grid{display:grid;gap:.75rem;margin:.75rem 0}
.rp-g3{grid-template-columns:repeat(3,minmax(0,1fr))}.rp-g2{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:760px){.rp-g3,.rp-g2{grid-template-columns:1fr}}
.rp-label{font-size:.85rem;font-weight:600}
.rp-grade{font-size:1.9rem;font-weight:700;letter-spacing:-.03em;margin:.35rem 0 .1rem 0}
.rp-grade span{font-size:1rem;font-weight:500;color:var(--muted);margin-left:.35rem}
.rp-bar{position:relative;height:.4rem;border-radius:999px;background:var(--subtle);margin:.6rem 0 .55rem 0}
.rp-bar>i{position:absolute;left:0;top:0;bottom:0;border-radius:999px;background:#18181b}
.rp-bar>b{position:absolute;top:-.25rem;bottom:-.25rem;width:2px;background:#ef4444;border-radius:2px}
.rp-title{font-size:1.35rem;font-weight:700;letter-spacing:-.02em;margin:.5rem 0 .25rem 0}
.rp-meta{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.75rem}
.rp-alert{border:1px solid #fecaca;background:#fef2f2;border-radius:var(--radius);padding:.8rem 1rem;margin:.5rem 0;color:#7f1d1d}
.rp-alert.ok{border-color:#bbf7d0;background:#f0fdf4;color:#14532d}
.rp-alert b{display:block;margin-bottom:.15rem;color:inherit}
.rp-alert .rp-muted{color:inherit;opacity:.8}
.rp-section-label{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:1.2rem 0 .2rem 0}
.rp-stat{font-size:1.5rem;font-weight:700;letter-spacing:-.02em;margin-top:.2rem}
.rp-pre{white-space:pre-wrap;font-size:.875rem;line-height:1.55;background:var(--soft);border:1px solid var(--border);
  border-radius:.6rem;padding:.9rem 1rem;max-height:340px;overflow:auto;color:#27272a}
.rp-check{display:flex;gap:.55rem;align-items:flex-start;margin:.35rem 0;font-size:.9rem}
.rp-check>span:first-child{flex:none;width:1.15rem;height:1.15rem;border-radius:999px;background:#18181b;color:#fff;font-size:.7rem;
  display:flex;align-items:center;justify-content:center;margin-top:.12rem}
.rp-mail-h{display:grid;grid-template-columns:5.5rem 1fr;gap:.25rem .5rem;font-size:.875rem;padding-bottom:.7rem;
  border-bottom:1px solid var(--border);margin-bottom:.7rem}
.rp-mail-h>div:nth-child(odd){color:var(--muted)}
.rp-date{flex:none;width:3.6rem;border:1px solid var(--border);border-radius:.6rem;overflow:hidden;text-align:center}
.rp-date>div:first-child{background:#ef4444;color:#fff;font-size:.7rem;font-weight:600;padding:.1rem 0;text-transform:uppercase}
.rp-date>div:last-child{font-size:1.35rem;font-weight:700;padding:.2rem 0}
.rp-side-brand{font-size:1.15rem;font-weight:700;letter-spacing:-.02em}
.rp-flow{font-size:.8rem;color:var(--muted);line-height:1.9}
.rp-flow b{color:var(--fg);font-weight:500}
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
       f'<div class="rp-muted" style="font-size:.95rem;color:#3f3f46">{esc(human(v.get("summary", "")))}</div>'
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
       f'<div class="rp-muted" style="font-size:.78rem;margin-top:-.2rem">Red tick = pass mark.</div>')

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
        ui(f'<div class="rp-muted" style="font-size:.95rem;color:#3f3f46;margin-bottom:.6rem">{esc(red["why_recommended"])}</div>')
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
    with st.container(border=True):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        to = c1.text_input("Lecturer email", value=v.get("lecturer_email", "") if "@" in v.get("lecturer_email", "") and
                           "REPLACE" not in v.get("lecturer_email", "") else os.environ.get("DEMO_LECTURER_EMAIL", ""),
                           placeholder="lecturer@university.edu.my")
        approve = c2.button(f"✅ Approve {pick}", type="primary", width="stretch")
        if not unlocked():
            ui('<div class="rp-muted" style="font-size:.8rem">🔒 Approve works for everyone and shows every follow-up below. '
               'Writing the real Jira card needs the judge password (sidebar).</div>')
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
    if rf.smtp_configured() and to and unlocked():
        try:
            att = [(f"{v.get('module')}_{v.get('assessment')}_revised.txt", revised.encode(), "text/plain")]
            if ics:
                att.append(("redpen-review.ics", ics.encode(), "text/calendar"))
            rf.send_email(to, rf.email_subject(v), rf.email_body(v, red, opt), att)
            log.append(("Email", f"report sent to {to}" + (" with the review invite" if ics else "")))
        except Exception as e:  # noqa: BLE001
            log.append(("Email", f"⚠️ {e}"))
    else:
        log.append(("Email", "ready in the outbox below: read it on screen or download it (.eml opens in any mail app)."))
    if ics:
        log.append(("Calendar", f"30-min T&L review for {rf.next_working_day_10am():%a %d %b, 10:00} MYT (in the outbox below)"))
    log.append(("Revised brief", "ready to download below"))
    st.session_state[f"done-{name}"] = log


def show_downloads(v, red, opt, brief_text, name):
    with st.container(border=True):
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
        with st.container(border=True):
            try:
                i = rf.jira_issue(key)
                ui(f'<div class="rp-row"><span class="rp-label">Jira · Assessment Exposure Register</span>'
                   f'{badge("Read back live from Jira", "gray")}</div>'
                   f'<div class="rp-row" style="justify-content:flex-start;gap:.5rem;margin:.7rem 0 .3rem 0">'
                   f'{badge(i["key"], "solid", "lg")}{badge(i["status"], "green", "lg")}'
                   f'<span style="font-weight:600">{esc(i["summary"])}</span></div>'
                   f'<div class="rp-meta">{"".join(badge(lb) for lb in i["labels"])}</div>'
                   f'<div class="rp-muted" style="margin-top:.5rem;font-size:.8rem">Updated {esc(i["updated"])}</div>')
                st.link_button("Open the card in Jira ↗", i["url"])
            except ra.AuditError as e:
                st.warning(f"Could not read the card back: {e}")

    atts = [(f"{base}_revised.txt", revised.encode(), "text/plain")]
    if ics:
        atts.append(("redpen-review.ics", ics.encode(), "text/calendar"))
    with st.container(border=True):
        ui('<div class="rp-row" style="margin-bottom:.7rem"><span class="rp-label">Email to the lecturer</span>'
           f'{badge("Report", "gray")}</div>'
           '<div class="rp-mail-h">'
           f'<div>From</div><div>RedPen</div><div>To</div><div>{esc(to or "(lecturer email)")}</div>'
           f'<div>Subject</div><div style="font-weight:600">{esc(rf.email_subject(v))}</div>'
           f'<div>Attached</div><div>{"".join(badge("📎 " + a[0]) + " " for a in atts)}</div></div>'
           f'<div class="rp-pre" style="background:#fff;border:none;padding:0;max-height:420px">{pre(rf.email_body(v, red, opt))}</div>')
        st.download_button("Download this email (.eml)", rf.email_eml(to, rf.email_subject(v), rf.email_body(v, red, opt), atts),
                           f"{base}_redpen-report.eml", mime="message/rfc822", key=f"eml-{name}")

    if ics:
        e = rf.calendar_event(v, to)
        with st.container(border=True):
            ui('<div class="rp-row" style="margin-bottom:.7rem"><span class="rp-label">Calendar · T&amp;L review meeting</span>'
               f'{badge("Booked because exposure is HIGH", "red")}</div>'
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

    with st.container(border=True):
        ui('<div class="rp-label" style="margin-bottom:.6rem">Files</div>')
        c1, c2, _ = st.columns([1, 1, 1])
        c1.download_button("Revised brief (.txt)", revised, f"{base}_revised.txt", key=f"rev-{name}", width="stretch")
        c2.download_button("Verdict (.json)", json.dumps(v, indent=2), f"{base}_verdict.json", mime="application/json",
                           key=f"ver-{name}", width="stretch")
        with st.expander("Preview the revised brief"):
            st.text(revised[:6000])


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    ui('<div class="rp-side-brand">🖍️ RedPen</div><div class="rp-muted" style="margin-bottom:1rem">'
       'They catch students. We fix assignments.</div>')
    mode = st.radio("Mode", ["Saved audits (instant)", "Run a new audit"], index=0)
    st.divider()
    if os.environ.get("APP_PASSWORD") and not st.session_state.get("pw_ok"):
        pw = st.text_input("Judge password", type="password", help="Unlocks the real Jira write and live audits.")
        if pw:
            st.session_state.pw_ok = pw == os.environ["APP_PASSWORD"]
            if not st.session_state.pw_ok:
                st.error("Wrong password")
    elif os.environ.get("APP_PASSWORD"):
        ui(badge("🔓 Unlocked: real Jira + live audits", "green"))
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
    if rf.jira_configured():
        ui('<div class="rp-section-label">Live from Jira · RP board</div>')
        try:
            st.dataframe(rf.jira_register(), hide_index=True, width="stretch")
            st.caption("Every lecturer approval creates or updates one card here. The Gemini Enterprise version uses the Jira Cloud connector.")
        except ra.AuditError as e:
            st.caption(f"Jira not reachable right now: {e}")
else:
    if not unlocked():
        st.warning("Enter the judge password in the sidebar to run a live audit (each run uses 6 Gemini calls). "
                   "Saved audits work without it.")
        st.stop()
    step(1, "Audit a new assessment", "Upload a brief and its rubric (PDF, DOCX or TXT). Takes about 1–5 minutes.")
    with st.container(border=True):
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
