---
inclusion: fileMatch
fileMatchPattern: "ghost_signal/**/*.py"
---
# SMS rules (never break these)

- A reply fits in at most `GHOST_MAX_SEGMENTS` (3) SMS parts. GSM-7: 160 characters alone,
  153 per part when split; extended characters count double. UCS-2 (Lao, Arabic, most accents,
  any emoji): 70 alone, 67 per part. Always pass replies through `sms.fit()`.
- Never put emoji or curly quotes in replies: one emoji turns the whole SMS into UCS-2 and
  can double the cost. Strip accents from place names (`sources._ascii`).
- STOP always wins. A single-word STOP / local stop word opts out and cancels reminders.
  Nothing is sent to an opted-out number until START.
- Answer each Twilio MessageSid once. Twilio may call the webhook again.
- Every path returns something to the phone (a short apology on failure), except for
  opted-out numbers and duplicate webhooks, which get an empty reply.
- Never log or store message texts; mask phone numbers in logs (`countries.mask`).
- Health and safety answers say "see a health worker" in the reply language.
