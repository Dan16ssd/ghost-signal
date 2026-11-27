# Design: every language works with no AI key

## Files
```
ghost_signal/data/
  call_scripts.json        {"ru": {"intro": "...", "press": "...", "thanks": "...", "retry": "...",
                                   "_review": "machine-written, agent-reviewed"}, ...}
  messages/
    es.json                {"_review": "machine-written, agent-reviewed", "help": "...", ...29 keys}
    hi.json ...
```
- JSON, UTF-8, one language per message file, so a native speaker can review one file at a time.
- Keys starting with `_` are notes, not messages; the loader skips them.
- The hand-written scripts and messages in `meds.py` / `lang.py` (en, lo, ar, es, fr, pt, hi, tl, th)
  stay in code and **win** over data files.

## Loader (`ghost_signal/data/__init__.py`)
```python
def load_call_scripts() -> dict[str, dict[str, str]]   # merged into meds.SCRIPT where missing
def load_messages() -> dict[str, dict[str, str]]       # merged into lang.MESSAGES where missing
```
- Called once at import of `meds` and `lang`; a broken file logs an error and is skipped (the app
  still starts).
- After loading, `answer.message()` already prefers `L.MESSAGES[language]` over AI, and
  `answer.call_voice()` already prefers `meds.SCRIPT[spoken]`, so no change is needed there.
- `Dockerfile` copies the package, so `data/` ships with it (check `.dockerignore`).

## Lao -> Thai transliteration (`ghost_signal/lao_thai.py`)
- A table of Lao consonants, vowels, tone marks and digits to Thai (e.g. ກ->ก, ຂ->ข, ຄ->ค, ງ->ง,
  ຢ->ย, າ->า, ່->่, ໆ->ๆ, ໐-໙->๐-๙). Kiro drafts the table; Danny checks it.
- `to_thai(text) -> str | None`: None if any Lao letter is not in the table.
- `answer._spoken_what()` uses it when AI is off (today it returns "" for Lao).

## Tests (`tests/test_offline_languages.py`)
- Every voice language has a call script with the 4 keys; `press` contains "1"; each line <= 120 chars.
- Every message file has exactly the 29 English keys (ignoring `_` notes).
- Every command word and every number/phone number in the English message appears in the translation.
- Every message fits `sms.segments(...) <= 2` (help included).
- With `use_llm=False`: `answer.call_voice("ru")` returns the Russian script and a Russian voice;
  `answer.message("help", "sw")` is not English.
- Property test (Hypothesis): `to_thai` on any string of mapped Lao letters returns Thai letters
  only and has the same length.

## Kiro workflow
1. Run the spec tasks in Kiro; Kiro writes the JSON files from the English sources.
2. The `language-review` hook runs on save of `ghost_signal/data/**` and calls the
   `language-reviewer` agent (meaning, natural wording, length via the MCP `check_sms` tool).
3. Fix what the agent flags; commit.
