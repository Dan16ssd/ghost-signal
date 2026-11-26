# Design: medicine reminder calls

## Data (store.py)
- `meds(number, times "08:00,20:00", what, spoken, lang, tz, active)` - `spoken` is what the
  voice says (Lao -> Thai translation, done once when the medicine is set).
- `doses(med_id, due, next_try, attempts, state, ring_pending)` - exactly one waiting dose per
  medicine; finishing a dose (confirmed or missed) plans the next with `meds.next_due`.
- `family(person, contact, ok)`.

## Flow
```
MEDS 8am pill --> meds row + first dose (next 8am, local)
tick (20 s): dose due --> call #1 (Twilio Calls API, Url=/voice/dose/{id})
   Twilio --> POST /voice/dose/{id} --> <Gather numDigits=1><Say>...</Say></Gather>
   person presses 1 --> POST /voice/answer/{id} --> confirmed, next dose planned
   no 1 --> next_try +10 min --> call #2 --> no 1 --> missed --> SMS to family (ok=1)
```
- Voices: `meds.VOICES` maps language -> Twilio `<Say>` language and voice (Polly / Google).
  Lao has none, so `SPOKEN_AS = {"lo": "th"}` and a hand-written Thai script.
  Hand-written scripts: English, Arabic, Thai; other voiced languages: AI translation, cached.
- Fallbacks: no voice for the language, voice calls off, no public URL or the daily call cap
  reached -> SMS "MEDICINE TIME: ... Reply 1 when you have taken it."
- Simulator: web senders never get real calls; the dose sets `ring_pending` and `/api/inbox`
  returns it as a call; `/api/dose/{id}/press` is allowed only for the same web sender.

## Why press 1, not voice chat
Key presses work on every phone, in noise, for people with weak speech, and cost less.
An AI voice conversation could come later.
