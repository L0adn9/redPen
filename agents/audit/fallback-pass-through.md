# Fallback: pass-through mode (only if day-1 check #13 fails)

**When to use this:** the Examiner needs the Intake JSON *and* all three persona outputs, and the Verdict needs the Intake JSON *and* the Examiner output. Google's docs say steps run "in sequence" and pass "variables", but they don't say whether a step can use the output of *any* earlier step or only the one just before it.

If check #13 shows a step can only use the step just before it, switch to **pass-through mode**: each step copies forward everything later steps need, so the data travels down the chain as one growing "bundle".

```
Intake ──► Copy-paster ──► Prompt engineer ──► Honest helper ──► Examiner ──► Verdict
 {intake}   {intake,        {intake,             {intake,           {meta,        verdict
             attempts:{cp}}  attempts:{cp,pe}}    attempts:{cp,pe,hh}} examiner}    JSON
```

The step instructions don't change, except for the paragraphs below. Paste each one **at the end** of that step's instructions, and set the step's output JSON shape to the one shown.

---

### Persona 1: Copy-paster (`02-persona-copy-paster.md`)
```
PASS-THROUGH RULE: Your input is the Intake JSON. Your output must be a single JSON object:
{"intake": <the Intake JSON copied exactly, unchanged>,
 "attempts": {"copy_paster": [{"task_id": "T1", "answer": "..."}]}}
Do not change anything inside "intake".
```

### Persona 2: Prompt engineer (`03-persona-prompt-engineer.md`)
```
PASS-THROUGH RULE: Your input is {"intake": {...}, "attempts": {...}}. Read the task text, rubric and AI policy from "intake".
Your output must be the same object with your answers added:
{"intake": <copied exactly>,
 "attempts": {"copy_paster": <copied exactly>, "prompt_engineer": [{"task_id": "T1", "answer": "..."}]}}
Do not change anything you copied.
```

### Persona 3: Honest helper (`04-persona-honest-helper.md`)
```
PASS-THROUGH RULE: Your input is {"intake": {...}, "attempts": {...}}. Read the task text and AI policy from "intake".
Your output must be the same object with your answers added:
{"intake": <copied exactly>,
 "attempts": {"copy_paster": <copied exactly>, "prompt_engineer": <copied exactly>, "honest_helper": [{"task_id": "T1", "answer": "..."}]}}
Do not change anything you copied.
```

### Examiner (`05-examiner.md`)
```
PASS-THROUGH RULE: Your input is {"intake": {...}, "attempts": {"copy_paster": [...], "prompt_engineer": [...], "honest_helper": [...]}}.
Read the rubric, selected_tasks, pass_mark and ai_policy from "intake", and the three attempts from "attempts".
Your output must be:
{"meta": {"module": ..., "module_name": ..., "assessment": ..., "brief_path": ..., "lecturer_email": ..., "pass_mark": ..., "clos": <intake.clos copied exactly>},
 "examiner": <your normal Examiner output>}
Do NOT copy the persona answers forward; the Verdict does not need them.
```

### Verdict (`06-verdict.md`)
```
PASS-THROUGH RULE: Your input is {"meta": {...}, "examiner": {...}}. Use "meta" wherever these instructions say "Intake JSON", and "examiner" for the Examiner JSON.
```

---

## Things to watch in this mode
- **Size:** the bundle gets large by the Examiner step. If runs time out, cut each persona's word limit (600 → 400) before anything else.
- **Copy drift:** spot-check that `intake.rubric` in the Examiner's input still matches the Intake output, i.e. that no step has "tidied" it.
- **Simpler alternative:** merge the three personas into **one** "Personas" step that outputs all three attempts in one JSON. This cuts the chain to Intake → Personas → Examiner → Verdict. It's less impressive on the canvas, and more likely to time out, so try the bundle first.
