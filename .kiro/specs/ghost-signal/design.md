# Design: Ghost Signal

```
Phone --SMS--> Twilio --POST /sms--> app.py --(background)--> answer.handle()
                                                          |-> commands (HELP, WEATHER)
                                                          |-> sources.wikipedia(lo, then en)
                                                          |-> Claude: answer only from sources, cite [n]
                                                          |-> sms.fit(<= 3 parts) + source link
Phone <--SMS-- Twilio <--Messages API-- twilio_sms.send_sms()
Browser simulator --POST /api/ask--> answer.handle()  (same engine)
```

## Key decisions
- **Reply later, not inline:** Twilio waits 15 s for a webhook; search + AI can be slower,
  so the webhook returns empty TwiML and the answer is sent through the API.
- **Sources first, AI second:** the AI only rewrites what trusted sources say, which keeps
  answers checkable and lets the service work (worse) without AI.
- **SMS length is a hard rule:** `sms.fit()` is property-tested so no input can exceed the limit.
- **No storage:** nothing is written to disk; the rate limiter is in memory.

## Error handling
Every failure path ends in a fixed short message in the sender's language.
