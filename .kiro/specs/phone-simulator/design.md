# Design: phone simulator

- One static file, no build step: `ghost_signal/static/index.html`, served at `/`.
- `/api/ask {text, country}` returns reply, parts, encoding, kind and language; the hint line
  is chosen from `kind`. `/api/inbox` is polled every 15 s for due reminders.
- Multi-tap: last key and a 900 ms timer; a repeat tap replaces the last letter.
- Clear: a tap deletes a letter, holding 0.6 s clears the screen.
