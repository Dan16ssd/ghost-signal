# Design: reminders

- `reminders.parse(text, now)`: regexes for "in N unit" and clock times; `now` is an aware
  datetime in the Sender's zone. "In N hours" is added in UTC (real elapsed time); clock
  times compare by timestamp, and a time skipped by daylight saving moves to the next day.
- AI fallback prompt gives the local date, time and weekday and asks for
  `{"when": "YYYY-MM-DDTHH:MM", "what": ...}` or `NONE`; `parse_ai_reply` validates it.
- Storage: `reminders` table with the due time as a Unix timestamp and the label the Sender saw.
- Delivery: `app.deliver_due_reminders()` every 20 s in a background task. States:
  waiting -> sent | inbox -> sent | cancelled | failed. Never sent twice.
- Property test: for any clock time, any start minute over two years and four time zones
  (one with daylight saving), the due time is after now and within 25 hours.
