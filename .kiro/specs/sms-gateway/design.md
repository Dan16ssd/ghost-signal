# Design: SMS gateway

- `store.py`: one SQLite file (`GHOST_DB`), a single connection guarded by a lock
  (FastAPI runs sync handlers in a thread pool). Tables: `optout`, `seen`, `hits`,
  `usage(day, kind)`, `reminders`.
- STOP/START are handled first in `answer.handle()`, so the simulator, the MCP server and
  SMS share one rule. Opted-out numbers get a `silent` reply (empty text) and the webhook
  returns empty TwiML.
- The duplicate check happens before rate limiting, so a Twilio retry does not count twice.
- AI budget: `answer._claude()` checks and counts `usage(today, "ai")` before each call and
  raises `BudgetSpent`, which every caller already handles by falling back to extracts.
- `/health` reads `store.stats()`.

Trade-off: SQLite on a free host's disk can be wiped on redeploy. For the hackathon that
only loses reminders and limits; a mounted volume or Postgres is the production upgrade.
