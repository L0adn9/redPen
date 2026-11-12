#!/usr/bin/env python3
"""RedPen Insight (prototype): the chat agent over the Assessment Exposure Register.

Uses the EXACT instructions from agents/audit/07-insight-chat-agent.md. In Gemini Enterprise the sources are
Jira project RP + Drive; in the prototype the register is the saved verdict files (data/demo-runs/) plus any
verdicts the app produced this session.

    from redpen_insight import ask, register
    ask("Which CLOs in my programme are at risk?")                 # -> answer text (markdown)
    ask("...", extra_verdicts=[verdict_dict, ...], history=[("user", "..."), ("assistant", "...")])

    python3 tools/redpen_insight.py "Which of my assessments are HIGH?"
"""
import json
import re
import sys

from redpen_audit import AUDIT, DEMO, AuditError, api_key, call, demo_runs, load_demo

PROTOTYPE_NOTE = """PROTOTYPE SOURCES: Jira and Drive are not connected in this prototype. The register below is the full set of
verdict files (one per audit), each with its redesign status. Treat it as Jira project RP + Drive /RedPen/Verdicts/.
Cite a verdict as "<MODULE> <ASSESSMENT> verdict (<audit_date>)". Answer in markdown.
Return JSON only: {"answer": "<markdown answer>", "sources": ["<MODULE> <ASSESSMENT>", ...]}"""


def instructions():
    text = (AUDIT / "07-insight-chat-agent.md").read_text(encoding="utf-8")
    m = re.search(r"^## Instructions.*?^```[a-z]*\n(.*?)^```", text, re.S | re.M)
    if not m:
        raise AuditError("no instructions block found in 07-insight-chat-agent.md")
    return m.group(1).strip()


def register(extra_verdicts=()):
    """Compact register rows: one per assessment, newest verdict wins."""
    rows = {}
    for name in demo_runs():
        r = load_demo(name)
        v = dict(r["verdict"])
        red = r["steps"].get("07-redesign")
        v["_status"] = "Redesign proposed" if red else "Audited"
        if red:
            v["_redesign_options"] = [{k: o.get(k) for k in ("id", "title", "aias_level", "lane", "techniques",
                                                             "extra_marking_minutes_per_student")}
                                      for o in red.get("options", [])]
            v["_recommended"] = red.get("recommended")
        rows[(v.get("module"), v.get("assessment"))] = v
    for v in extra_verdicts:
        rows[(v.get("module"), v.get("assessment"))] = dict(v, _status=v.get("_status", "Audited"))
    keep = ("module", "module_name", "assessment", "exposure", "model", "audit_date", "persona_grades",
            "persona_totals", "pass_mark", "clos_at_risk", "easy_criteria", "summary",
            "_status", "_redesign_options", "_recommended")
    return [{k: v[k] for k in keep if k in v} for v in rows.values()]


def ask(question, extra_verdicts=(), history=(), key=None):
    """Answer one question. history: [(role, text), ...] of earlier turns (kept short)."""
    if not (question or "").strip():
        raise AuditError("empty question")
    key = key or api_key()
    convo = "\n".join(f"{r.upper()}: {t}" for r, t in list(history)[-6:])
    user = (PROTOTYPE_NOTE + "\n\nREGISTER:\n" + json.dumps(register(extra_verdicts), ensure_ascii=False)
            + (f"\n\nEARLIER CONVERSATION:\n{convo}" if convo else "") + f"\n\nQUESTION: {question.strip()}")
    for attempt in range(2):
        text, _ = call(instructions(), user, key)
        try:
            data = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()), strict=False)
            if isinstance(data, dict) and data.get("answer"):
                return data["answer"]
        except json.JSONDecodeError:
            if text.strip() and not text.strip().startswith("{") and attempt == 1:
                return text.strip()  # plain-text answer is still usable
    raise AuditError("Insight did not return an answer")


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Which CLOs in my programme are at risk?"
    print(ask(q))
