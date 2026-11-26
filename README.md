# 👻 Ghost Signal

[![tests](https://github.com/Dan16ssd/ghost-signal/actions/workflows/tests.yml/badge.svg)](https://github.com/Dan16ssd/ghost-signal/actions/workflows/tests.yml)

**No smartphone? No data? Text your question and the web texts back.**

Ghost Signal brings the web to a "dead" technology: plain SMS on basic phones.
Text a question to the Ghost Signal number; it searches trusted public sources
(Wikipedia, Open-Meteo weather, exchange rates) and texts back a short answer
with its source, **in the language you wrote in** (50+ languages).

We are a two-person team from **Laos and Egypt**, so those are our launch countries,
with hand-written Lao and Arabic. It works from any of 93 countries: your phone
number tells Ghost Signal where you are, so `RATE` shows *your* money.

Built for **Kiroween 2026**, category **Resurrection**.

## Try it

- **By SMS:** text `HELP` to the Ghost Signal number *(number added at launch)*.
- **In the browser:** open the old-phone simulator at `/` (same answer engine).

| Message | Reply |
|---|---|
| `What is dengue fever?` | 1-3 SMS answer + source link |
| `WEATHER Vientiane` | Now + tomorrow forecast |
| `RATE` / `سعر USD` / `ອັດຕາ USD` | Dollar in Egyptian pounds, kip... |
| `ໄຂ້ຍຸງລາຍ ແມ່ນຫຍັງ` | Answer in Lao |
| `ما هي حمى الضنك؟` | Answer in Arabic |
| `طقس القاهرة` | Cairo forecast |
| `Dalili za malaria ni zipi?` (from Kenya) | Answer in Swahili |
| `डेंगू के लक्षण क्या हैं?` (from India) | Answer in Hindi |
| `RATE` (from Nigeria) | Dollar in naira |
| `REMIND 8pm take medicine` | An SMS at 8pm **in your own time zone** |
| `REMIND in 2 hours call mum` / `REMIND LIST` / `REMIND DEL 1` | Set, list, delete |
| `ذكرني غدا الساعة 8 مساء بالدواء` | Reminder set in Arabic, Cairo time |
| `STOP` / `START` | No more texts / welcome back |
| `HELP` | Commands |

## Why

Hundreds of millions of people have a phone but no smartphone or no mobile data.
In rural Laos and in Upper Egypt, a basic phone and SMS still reach people that apps
don't, and prices change fast (kip and Egyptian pound), so a trusted health fact, a
forecast or today's exchange rate makes a daily difference. Ghost Signal gives them
answers from the open web through the oldest messaging channel phones have.
The same need exists from Lagos to Dhaka, so the engine is not tied to one country.

## How it works

```
Phone --SMS--> Twilio --webhook--> /sms --> search trusted sources --> AI writes a short,
                                                                       sourced answer
Phone <--SMS-- Twilio <--API------ fit to <= 3 SMS parts (67 chars each in Lao/Arabic)
```

- **Country** comes from the sender's calling code (+20 Egypt, +856 Laos, +254 Kenya...;
  `ghost_signal/countries.py`): it sets the local currency and breaks language ties.
- **Language** comes from the text: its alphabet (Lao, Arabic, Devanagari, Cyrillic, Han...)
  or common words for Latin-script languages; the country decides ties (Arabic vs Persian letters).
- It searches **that language's Wikipedia** first; if the page doesn't answer, it turns the
  question into English, searches English Wikipedia, and still replies in the person's language.
- Fixed messages are hand-written in English, Lao and Arabic; other languages get an
  AI translation, made once and cached.
- Answers come **only** from sources; if nothing fits, it says so instead of guessing.
- Every reply fits in at most 3 SMS parts. This rule is checked by property-based tests.
- Health answers always add "see a health worker".
- **Reminders** use the time zone of the sender's country and arrive as a new SMS.
- **Built like a real SMS service:** `STOP` always wins (opt-out also cancels reminders),
  each Twilio message is answered once even if Twilio retries, each number gets 20 questions
  an hour, all AI calls together have a daily budget (above it, answers fall back to plain
  source extracts), and phone numbers are masked in logs. Message texts are never stored.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in GHOST_CONTACT (required by Wikipedia), keys optional
uvicorn ghost_signal.app:app --reload
# open http://127.0.0.1:8000
python -m pytest -q          # tests (no network needed)
python -m ghost_signal.mcp_server   # Ghost Signal as an MCP server (tools for Kiro / any MCP client)
```

### Deploy

`Dockerfile` + `render.yaml` (Render free tier): create a Blueprint from this repo, then set
`ANTHROPIC_API_KEY`, the Twilio values and `PUBLIC_BASE_URL` in the dashboard. Mount a disk
at `/data` to keep opt-outs and reminders across redeploys.

Without an Anthropic key, answers fall back to the first sentences of the source.

### Connect Twilio

1. Buy an SMS-capable number in Twilio.
2. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `PUBLIC_BASE_URL` in `.env`.
3. In the number's settings, set **A message comes in** to `POST https://<your-host>/sms`.

## How we used Kiro

| Kiro feature | Where | What it does for us |
|---|---|---|
| **Specs** (5) | `.kiro/specs/` | `ghost-signal`, `sms-gateway`, `reminders`, `phone-simulator`, `mcp-server`: EARS requirements, design, tasks |
| **Steering** (6) | `.kiro/steering/` | product, tech, structure, plus `sms-rules`, `languages`, `design` that load only for matching files |
| **Hooks** (4) | `.kiro/hooks/` | tests on save, secret + phone-number scan, HELP/README sync, language review of Lao/Arabic |
| **Custom agents** (2) | `.kiro/agents/` | `language-reviewer`, `gateway-auditor` |
| **MCP** | `.kiro/settings/mcp.json` | Ghost Signal *is* an MCP server: the agent tests real replies in any language with `ask` and `check_sms` |
| **Property tests** | `tests/` | SMS length for any text; reminder times for any clock time in four time zones (it caught a daylight-saving bug) |

Full story: [`docs/kiro-journal.md`](docs/kiro-journal.md). *(Detailed write-up with screenshots in progress.)*

## License

MIT
