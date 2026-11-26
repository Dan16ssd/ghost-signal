# Tech

- Python 3.12, FastAPI, httpx. No database.
- SMS: Twilio. Webhook `POST /sms`; signature checked with `TWILIO_AUTH_TOKEN`.
  When Twilio send credentials exist, reply with empty TwiML and send the answer
  through the Twilio API in a background task (avoids the 15 s webhook limit).
- Sources: Wikipedia (lo + en) and Open-Meteo. No keys. The User-Agent must contain
  contact info (`GHOST_CONTACT`) or Wikipedia returns 403.
- AI: Anthropic SDK, model `claude-opus-5-5`, effort `low`, server-side refusal
  fallbacks on. Without credentials, fall back to the first sentences of the source.
- Secrets only in `.env` (git-ignored). `.env.example` lists every setting.
- Tests: pytest + Hypothesis property tests. Tests never touch the network.

## Commands
- Install: `pip install -r requirements.txt`
- Run: `uvicorn ghost_signal.app:app --reload`
- Test: `python -m pytest -q`
