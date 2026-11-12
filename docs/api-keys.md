# API keys and switching them (demo day)

RedPen only calls **Google Gemini** models (hackathon rule). `tools/redpen_audit.py` refuses any other model.

Two ways to reach Gemini, used **cheapest first**:

| Order | Provider | Key name | Models (default) | Cost |
|---|---|---|---|---|
| 1 | Google AI Studio | `GEMINI_API_KEY` | `gemini-3-flash-preview` (the model we calibrated), `gemini-3.5-flash` | **Free** (about 20 calls/day per model; one audit = 6 calls) |
| 2 | OpenRouter | `OPENROUTER_API_KEY` (starts `sk-or-`) | `google/gemini-3.1-flash-lite`, `google/gemini-2.5-flash-lite`, then `google/gemini-3-flash-preview` | Paid, about $0.001–0.005 per audit |

The engine tries the free models first and only moves to OpenRouter when the free ones are out of quota, hang, or the free key
is rejected. **Pro (`google/gemini-4-argon`) is never used unless you ask for it** with `REDPEN_MODELS=google/gemini-4-argon`
(it costs about 4× Flash). `REDPEN_BACKEND=gemini` = free only; `REDPEN_BACKEND=openrouter` = paid only.
`REDPEN_MODELS` (comma-separated) overrides the list: `google/...` names go to OpenRouter, bare `gemini-...` names to AI Studio.

## Where keys go
- **Local:** `redPen/.env` (gitignored), one per line: `OPENROUTER_API_KEY=...` or `GEMINI_API_KEY=...`. The file is re-read on every audit, so editing it takes effect on the next run, no restart.
- **Streamlit Cloud:** app → Settings → Secrets, same names at the top level (Streamlit exposes them as environment variables).
- **Inside the app:** `set_credentials(key)` switches backend and key at runtime (an `sk-or-` key means OpenRouter, anything else means AI Studio). Put it behind the admin password.

## Swapping a key mid-demo
1. Put the new key in `.env` (local) or Streamlit Secrets (hosted), or paste it into the app's key box.
2. Check it: `python3 tools/redpen_audit.py --check` makes one tiny call per model and prints OK or the error.
3. If nothing works, switch the app to demo mode (saved runs, no API calls).

Never commit keys or show them on screen in the video.
