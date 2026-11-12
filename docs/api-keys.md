# API keys and switching them (demo day)

RedPen only calls **Google Gemini** models (hackathon rule). `tools/redpen_audit.py` refuses any other model.

Two ways to reach Gemini; the engine picks one automatically:

| Backend | Key name | Notes |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEY` (starts `sk-or-`) | Used whenever this key is set. Paid per token, no daily cap, has Pro (`google/gemini-4-argon`). |
| Google AI Studio | `GEMINI_API_KEY` | Free tier: about 20 calls a day per model, no Pro. One audit = 6 calls. |

Force one with `REDPEN_BACKEND=openrouter` or `REDPEN_BACKEND=gemini`. Change the model list with `REDPEN_MODELS` (comma-separated, tried in order; a model that's out of quota or hangs is skipped).

## Where keys go
- **Local:** `redPen/.env` (gitignored), one per line: `OPENROUTER_API_KEY=...` or `GEMINI_API_KEY=...`. The file is re-read on every audit, so editing it takes effect on the next run, no restart.
- **Streamlit Cloud:** app → Settings → Secrets, same names at the top level (Streamlit exposes them as environment variables).
- **Inside the app:** `set_credentials(key)` switches backend and key at runtime (an `sk-or-` key means OpenRouter, anything else means AI Studio). Put it behind the admin password.

## Swapping a key mid-demo
1. Put the new key in `.env` (local) or Streamlit Secrets (hosted), or paste it into the app's key box.
2. Check it: `python3 tools/redpen_audit.py --check` makes one tiny call per model and prints OK or the error.
3. If nothing works, switch the app to demo mode (saved runs, no API calls).

Never commit keys or show them on screen in the video.
