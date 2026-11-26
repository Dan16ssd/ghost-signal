# Tech

- Python 3.12, FastAPI, httpx, SQLite (one file, `GHOST_DB`) for opt-outs, limits, duplicate
  webhooks, the daily AI budget and reminders. Message texts are never stored.
- SMS: Twilio. Webhook `POST /sms`; signature checked with `TWILIO_AUTH_TOKEN`.
  When Twilio send credentials exist, reply with empty TwiML and send the answer
  through the Twilio API in a background task (avoids the 15 s webhook limit).
- Reminders: a background loop every 20 s sends due reminders; web visitors get them through
  `GET /api/inbox`. Time zones come from the sender's country (`countries.TIMEZONES`).
- Sources: Wikipedia (question's language, then en), Open-Meteo, ExchangeRate-API (open.er-api.com).
  No keys. The User-Agent must contain contact info (`GHOST_CONTACT`) or Wikipedia returns 403.
- AI: Anthropic SDK, model `claude-opus-5-5`, effort `low`, server-side refusal fallbacks on.
  Without credentials, or above `GHOST_MAX_AI_PER_DAY`, fall back to plain extracts.
- MCP: `python -m ghost_signal.mcp_server` exposes the engine as tools (ask, check_sms,
  detect_language, wikipedia_search, fixed_messages); Kiro config in `.kiro/settings/mcp.json`.
- Secrets only in `.env` (git-ignored). `.env.example` lists every setting.
- Tests: pytest + Hypothesis property tests. Tests never touch the network (in-memory DB).
- CI: GitHub Actions runs the tests on every push. Deploy: Dockerfile (+ `render.yaml`).

## Commands
- Install: `pip install -r requirements.txt`
- Run: `uvicorn ghost_signal.app:app --reload`
- Test: `python -m pytest -q`
- MCP server: `python -m ghost_signal.mcp_server`
