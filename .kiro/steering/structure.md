# Structure

- `ghost_signal/app.py`      web server: `/` simulator, `/api/ask`, `/sms`, `/health`, rate limit
- `ghost_signal/answer.py`   one message in -> one reply out (commands, search, AI, SMS fit)
- `ghost_signal/sources.py`  Wikipedia + Open-Meteo clients
- `ghost_signal/sms.py`      GSM-7 / UCS-2 length rules and `fit()`
- `ghost_signal/lang.py`     Lao detection + fixed Lao/English messages
- `ghost_signal/twilio_sms.py` signature check, TwiML, send SMS
- `ghost_signal/static/index.html` old-phone simulator
- `tests/`                   unit + property tests (network stubbed)

New sources go in `sources.py` and return `Source(title, text, url)`.
New commands go in `answer.handle()` before the search step.
