# Product: Ghost Signal

Ghost Signal brings a "dead" technology back to life: old button phones, SMS and plain
phone calls, with an AI behind them. Pitch: "Grandma's old phone just got an AI."

Hero feature: daily medicine calls in the person's language (press 1; family SMS after two
missed calls). Second: ask anything by SMS (health, weather, money) with sources. Third:
SMS reminders. Everything works in many languages, not only one.

## Who it is for
- Anyone with a basic (feature) phone, or a smartphone but no mobile data.
- Hero user: an older person living alone with a basic phone, and their family far away.
- Filmed in Laos (Danny's family); works in 50+ languages and 93 countries.
  The engine works from any country: the sender's calling code gives the country (currency,
  language hint) and the text gives the language (50+ languages, 93 countries).
  Both have many people offline or on prepaid basic phones, and fast-moving prices
  (kip, peso after disasters), so health facts, weather and exchange rates matter daily.
- Adding a country = one line in `countries.py`. Fixed messages for languages without a
  hand-written version are AI-translated once and cached.

## Principles
- Every reply must fit in at most 3 SMS parts (Lao uses 70 characters per part).
- Answer only from sources; say "not found" rather than guess.
- Health and safety answers always advise seeing a health worker.
- The phone must always get a reply, even when a source or the AI fails.
- Never store message contents; phone numbers are only kept in memory for the hourly limit.

## Hackathon
Kiroween 2026, category Resurrection. Judged on impact, Kiro use, design, idea, presentation.
