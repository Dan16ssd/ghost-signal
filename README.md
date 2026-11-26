# 👻 Ghost Signal

[![tests](https://github.com/Dan16ssd/ghost-signal/actions/workflows/tests.yml/badge.svg)](https://github.com/Dan16ssd/ghost-signal/actions/workflows/tests.yml)

**Grandma's old phone just got an AI.**

Ghost Signal brings a "dead" technology back to life: the old button phone, plain SMS and
ordinary phone calls, now with an AI brain behind them. No smartphone, no app, no data plan.

- 📞 **Medicine calls**: every day at the right time, the old phone rings and a voice says,
  *in the person's own language*, which medicine to take. They press 1. No answer twice?
  A family member gets an SMS.
- 💬 **Ask anything by SMS**: health, weather, today's money rate. The answer comes back in
  the language the question was written in, with its source.
- ⏰ **Reminders by SMS**, in the person's own time zone.

It speaks **50+ languages** (17 with a phone voice) and works from **93 countries**: the phone
number tells Ghost Signal where someone is. We film it in **Laos**, where Danny's family uses
basic phones.

Built for **Kiroween 2026**, category **Resurrection**.

## Try it

- **By SMS:** text `HELP` to the Ghost Signal number *(number added at launch)*.
- **In the browser:** open the old-phone simulator at `/` (same answer engine).

| Message | Reply |
|---|---|
| `MEDS 8am 8pm blood pressure pill` | **The old phone rings every day** at 8am and 8pm: "time for your medicine, press 1" |
| `MEDS FAMILY +8562055512345` | If 2 calls get no answer, that family member gets an SMS (after they reply YES) |
| `MEDS LIST` / `MEDS DEL 1` / `1` | See, stop, or confirm a dose by SMS |
| `ຢາ 8am ຢາຄວາມດັນ` (Lao) / `MEDS 9am pastilla` (Spanish) / `MEDS 8am दवा` (Hindi) | The call speaks that language |
| `What is dengue fever?` | 1-3 SMS answer + source link |
| `WEATHER Vientiane` | Now + tomorrow forecast |
| `RATE` / `ອັດຕາ USD` | Dollar in kip, pesos... (your local money) |
| `ໄຂ້ຍຸງລາຍ ແມ່ນຫຍັງ` | Answer in Lao |
| `Paano bumaba ang presyon ng dugo?` (from the Philippines) | Answer in Tagalog |
| `Dalili za malaria ni zipi?` (from Kenya) | Answer in Swahili |
| `डेंगू के लक्षण क्या हैं?` (from India) | Answer in Hindi |
| `RATE` (from Nigeria) | Dollar in naira |
| `REMIND 8pm take medicine` | An SMS at 8pm **in your own time zone** |
| `REMIND in 2 hours call mum` / `REMIND LIST` / `REMIND DEL 1` | Set, list, delete |
| `STOP` / `START` | No more texts / welcome back |
| `HELP` | Commands |

## Why

Many older people still use basic button phones: big keys, a battery that lasts for days,
nothing to update. Smartphone apps, chatbots and voice assistants left them out, and many of
them live alone, far from their children who moved to the city or abroad. Forgetting a dose
of blood-pressure or diabetes medicine is common, and nobody notices until something goes wrong.

The old phone can already do the two things they need: **ring** and **receive a text**.
Ghost Signal puts an AI behind those two old channels instead of asking people to learn a
new device. The same basic phone also keeps working when floods or storms cut power and data,
which happens every year in places like Laos.

## How it works

```
Phone --SMS--> Twilio --webhook--> /sms --> search trusted sources --> AI writes a short,
                                                                       sourced answer
Phone <--SMS-- Twilio <--API------ fit to <= 3 SMS parts (67 chars each in Lao/Arabic)
```

- **Country** comes from the sender's calling code (+856 Laos, +63 Philippines, +254 Kenya...;
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
- **Medicine calls** are for older people living alone: the phone rings at the same local
  time every day, a voice in their language says what to take, and they press 1. No answer
  twice -> a family member they chose gets an SMS. Only the person's own number is ever called.
  Call scripts are hand-written in English, Spanish, French, Portuguese, Hindi, Tagalog,
  Arabic and Thai, and AI-translated for the other voiced languages. There is no Lao voice,
  so Lao speakers hear Thai, which most Lao understand. Languages without a voice get an SMS.
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
4. For medicine calls, the number must support **Voice**; calls fetch `https://<your-host>/voice/dose/<id>` (needs `PUBLIC_BASE_URL`).

## How we used Kiro

| Kiro feature | Where | What it does for us |
|---|---|---|
| **Specs** (6) | `.kiro/specs/` | `ghost-signal`, `sms-gateway`, `reminders`, `medication-calls`, `phone-simulator`, `mcp-server`: EARS requirements, design, tasks |
| **Steering** (6) | `.kiro/steering/` | product, tech, structure, plus `sms-rules`, `languages`, `design` that load only for matching files |
| **Hooks** (4) | `.kiro/hooks/` | tests on save, secret + phone-number scan, HELP/README sync, language review of Lao/Arabic |
| **Custom agents** (2) | `.kiro/agents/` | `language-reviewer`, `gateway-auditor` |
| **MCP** | `.kiro/settings/mcp.json` | Ghost Signal *is* an MCP server: the agent tests real replies in any language with `ask` and `check_sms` |
| **Property tests** | `tests/` | SMS length for any text; reminder times for any clock time in four time zones (it caught a daylight-saving bug) |

Full story: [`docs/kiro-journal.md`](docs/kiro-journal.md). *(Detailed write-up with screenshots in progress.)*

## License

MIT
