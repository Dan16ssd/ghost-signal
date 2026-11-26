# 👻 Ghost Signal

**No smartphone? No data? Text your question and the web texts back.**

Ghost Signal brings the web to a "dead" technology: plain SMS on basic phones.
Text a question to the Ghost Signal number; it searches trusted public sources
(Wikipedia in Lao and English, Open-Meteo weather) and texts back a short answer
with its source, in Lao or English.

Built for **Kiroween 2026**, category **Resurrection**.

## Try it

- **By SMS:** text `HELP` to the Ghost Signal number *(number added at launch)*.
- **In the browser:** open the old-phone simulator at `/` (same answer engine).

| Message | Reply |
|---|---|
| `What is dengue fever?` | 1-3 SMS answer + source link |
| `WEATHER Vientiane` | Now + tomorrow forecast |
| `ໄຂ້ຍຸງລາຍ ແມ່ນຫຍັງ` | Answer in Lao |
| `HELP` | Commands |

## Why

Millions of people have a phone but no smartphone or no mobile data. In rural Laos a
basic phone and SMS still reach people that apps don't. Ghost Signal gives them answers
from the open web through the oldest messaging channel phones have.

## How it works

```
Phone --SMS--> Twilio --webhook--> /sms --> search trusted sources --> AI writes a short,
                                                                       sourced answer
Phone <--SMS-- Twilio <--API------ fit to <= 3 SMS parts (70 chars each in Lao)
```

- Answers come **only** from sources; if nothing fits, it says so instead of guessing.
- Every reply fits in at most 3 SMS parts. This rule is checked by property-based tests.
- Health answers always add "see a health worker".
- Each number is limited to 20 questions per hour. No message is stored.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in GHOST_CONTACT (required by Wikipedia), keys optional
uvicorn ghost_signal.app:app --reload
# open http://127.0.0.1:8000
python -m pytest -q          # tests (no network needed)
```

Without an Anthropic key, answers fall back to the first sentences of the source.

### Connect Twilio

1. Buy an SMS-capable number in Twilio.
2. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `PUBLIC_BASE_URL` in `.env`.
3. In the number's settings, set **A message comes in** to `POST https://<your-host>/sms`.

## How we used Kiro

*(Write-up in progress: specs, steering, hooks, MCP and property-based testing; see `.kiro/`.)*

## License

MIT
