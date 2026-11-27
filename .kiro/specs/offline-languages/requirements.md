# Requirements: every language works with no AI key

## Introduction
Ghost Signal must run for free: no paid AI key on the server. Today the running app uses AI to
translate two things that never change: the medicine call script (for 8 of the 16 call-voice
languages) and the fixed SMS messages (for every language except English, Lao and Arabic).
Without a key, those people get an English call or English texts.

The fix: Kiro writes these translations **once, while we build**, and we save them as data
files in the repo. The running app reads the files and needs no AI for them.

## Glossary
- **Call script**: the 4 lines of a medicine call: `intro`, `press`, `thanks`, `retry`.
- **Fixed message**: one of the 29 keys in `ghost_signal/lang.py` `MESSAGES["en"]` (help, meds_set, ...).
- **Voice language**: a language in `meds.VOICES` (a Twilio voice exists for it).
- **Data file**: a JSON file under `ghost_signal/data/`, written by Kiro and reviewed before commit.

## Requirement 1: Call scripts for every voice language
**User Story:** As an older person who speaks Russian, Vietnamese or Bengali, I want the medicine
call in my language, even when the server has no AI key.
1. THE SYSTEM SHALL have a call script for every voice language (missing today: bn, id, ja, ko, ru, tr, vi, zh).
2. WHEN a call is placed THE SYSTEM SHALL use the saved script and SHALL NOT call any AI for it.
3. EACH script line SHALL keep the name "Ghost Signal" and the digit "1" in the `press` line.
4. EACH line SHALL be short and polite, for an older listener (one sentence, at most 120 characters).

## Requirement 2: Fixed messages in the top languages
**User Story:** As a person texting in Spanish, Hindi or Swahili, I want help, confirmations and
errors in my language, without a paid AI.
1. THE SYSTEM SHALL have all 29 fixed messages in: es, fr, pt, hi, bn, sw, id, tl, vi, th, ru, tr, zh.
2. EACH translated message SHALL keep the English command words exactly (HELP, WEATHER, RATE,
   REMIND, REMIND LIST, REMIND DEL, MEDS, MEDS LIST, MEDS DEL, MEDS FAMILY, STOP, START, YES)
   and every number and phone number in the English message.
3. EACH message SHALL fit the same number of SMS parts as the rule in `sms-rules.md`
   (fixed messages at most 2 parts; GSM-7 153 characters, UCS-2 67 characters per part).
4. WHEN a language has no data file THE SYSTEM SHALL fall back as today (AI if a key exists, else English).

## Requirement 3: Lao is spoken correctly
**User Story:** As a Lao grandmother, I want to hear the medicine name in the call.
1. WHERE the medicine name is written in Lao THE SYSTEM SHALL transliterate it into Thai script
   by a fixed character table (Lao and Thai letters map closely), not by AI, so the Thai voice can say it.
2. WHERE a Lao letter has no Thai equivalent THE SYSTEM SHALL leave the name out of the call (as today).

## Requirement 4: Quality and honesty
1. EVERY data file SHALL be reviewed by the Kiro `language-reviewer` agent before commit.
2. Lao and Thai SHALL also be checked by Danny; other languages are marked
   "machine-written, agent-reviewed" in the file until a native speaker checks them.
3. Tests SHALL fail if a data file misses a key, drops a command word or number, or is too long.
