# Product: Ghost Signal

Ghost Signal brings the web back to "dead" technology: plain SMS on basic phones.
A person texts a question; the service searches trusted public sources and texts back
a short answer with its source.

## Who it is for
- Anyone with a basic (feature) phone, or a smartphone but no mobile data.
- Launch audiences are the team's home countries: Laos (Lao) and Egypt (Arabic), plus English.
  The engine works from any country: the sender's calling code gives the country (currency,
  language hint) and the text gives the language (50+ languages, 93 countries).
  Both have many people offline or on prepaid basic phones, and fast-moving prices
  (kip and Egyptian pound), so health facts, weather and exchange rates matter daily.
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
