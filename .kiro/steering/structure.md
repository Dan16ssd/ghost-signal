# Structure

- `ghost_signal/app.py`       web server: `/` simulator, `/api/ask`, `/api/inbox`, `/sms`, `/health`,
                              reminder delivery loop
- `ghost_signal/answer.py`    one message in -> one reply out (STOP/START, commands, search, AI, SMS fit)
- `ghost_signal/countries.py` calling code -> country, language, currency, time zone; number masking
- `ghost_signal/lang.py`      language detection (scripts, common words, country hint) + fixed messages
- `ghost_signal/reminders.py` REMIND time parsing (English rules, AI for other languages)
- `ghost_signal/store.py`     SQLite: opt-outs, rate limits, seen webhooks, AI budget, reminders
- `ghost_signal/sources.py`   Wikipedia, Open-Meteo, ExchangeRate-API clients
- `ghost_signal/sms.py`       GSM-7 / UCS-2 length rules and `fit()`
- `ghost_signal/twilio_sms.py` signature check, TwiML, send SMS
- `ghost_signal/mcp_server.py` the engine as MCP tools for Kiro
- `ghost_signal/static/index.html` old-phone simulator (multi-tap keypad, country picker, inbox)
- `tests/`                    unit + property tests (network stubbed, in-memory DB)
- `.kiro/specs/<feature>/`    one spec per feature: requirements, design, tasks

New sources go in `sources.py` and return `Source(title, text, url)`.
New commands go in `answer.handle()` after STOP/START and before the search step, with
local command words and fixed messages in English, Lao and Arabic.
