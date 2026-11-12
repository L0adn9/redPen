# API key and switching it (demo day)

RedPen only calls **Google Gemini** models (hackathon rule). `tools/redpen_audit.py` refuses any other model.

| Provider | Key name | Models, in order | Cost |
|---|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` (starts `sk-or-`) | `google/gemini-3-flash-preview` (the model we calibrated; all saved audits ran on it), then `google/gemini-3.1-flash-lite`, `google/gemini-2.5-flash-lite` as fallbacks | Paid, a few cents per audit |

If a model is out of quota, hangs or returns broken output, the step moves to the next model in the list.
**Pro (`google/gemini-4-argon`) is never used unless you ask for it** with `REDPEN_MODELS=google/gemini-4-argon`
(it costs about 4× Flash). `REDPEN_MODELS` (comma-separated) overrides the list.

We do **not** use the free Google AI Studio tier: it allows about 20 requests per model per day, and one audit needs 6–9,
so it runs dry after two audits. (The engine can still call it, but only if someone sets `REDPEN_BACKEND=gemini` on purpose.)

## Where the key goes
- **Local:** `redPen/.env` (gitignored): `OPENROUTER_API_KEY=sk-or-...`. The file is re-read on every audit, no restart.
- **Streamlit Cloud:** app → Settings → Secrets: `OPENROUTER_API_KEY = "sk-or-..."` (Streamlit exposes it as an environment variable).
- **GitHub Actions** (monthly re-audit): repo → Settings → Secrets and variables → Actions → `OPENROUTER_API_KEY`.
- **Inside the app:** with the judge password, the sidebar's *API key* box swaps the key at runtime.

## Swapping a key mid-demo
1. Put the new key in `.env` (local) or Streamlit Secrets (hosted), or paste it into the app's key box.
2. Check it: `python3 tools/redpen_audit.py --check` makes one tiny call per model and prints OK or the error.
3. If nothing works, use Saved audits (they replay instantly, no API calls).

Never commit keys or show them on screen in the video.
