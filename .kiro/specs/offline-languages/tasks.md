# Tasks: every language works with no AI key

Run these in Kiro, one at a time. Each task is small; test after each one.

- [ ] 1. Loader: create `ghost_signal/data/__init__.py` with `load_call_scripts()` and
      `load_messages()`; merge into `meds.SCRIPT` and `lang.MESSAGES` without overwriting
      hand-written entries; skip `_` keys; log and skip broken files
      _Requirements: 1.2, 2.4_
- [ ] 2. Tests first: `tests/test_offline_languages.py` with the checks in design.md
      (they fail until the data files exist)
      _Requirements: 4.3_
- [ ] 3. Call scripts: write `ghost_signal/data/call_scripts.json` for bn, id, ja, ko, ru, tr, vi, zh
      from the English script in `meds.py`; polite, short, for older listeners
      _Requirements: 1.1, 1.3, 1.4_
- [ ] 4. Messages, batch 1: es, fr, pt, hi, tl (the languages that already have call scripts)
      _Requirements: 2.1, 2.2, 2.3_
- [ ] 5. Messages, batch 2: bn, sw, id, vi, th, ru, tr, zh
      _Requirements: 2.1, 2.2, 2.3_
- [ ] 6. Hook: extend `.kiro/hooks/language-review.kiro.hook` to also run on
      `ghost_signal/data/**/*.json`; run the `language-reviewer` agent on every file and fix its findings
      _Requirements: 4.1_
- [ ] 7. Lao -> Thai: `ghost_signal/lao_thai.py` table + `to_thai()`; use it in
      `answer._spoken_what()` when AI is off; property test
      _Requirements: 3.1, 3.2_
- [ ] 8. Danny checks the Lao -> Thai table and listens to a Lao call in the simulator
      _Requirements: 4.2_
- [ ] 9. Check with no key: run the server without `ANTHROPIC_API_KEY`, press the 🇲🇽 🇮🇳 🇵🇭 🇱🇦
      demo buttons and a Russian/Vietnamese number in the simulator; every call and reply is in
      the right language
- [ ] 10. Update `README.md` (languages section), `.kiro/steering/languages.md` and
      `docs/kiro-journal.md`: "Kiro wrote every language once, so the app needs no paid AI"
- [ ] 11. Record this spec running in Kiro for the video (tasks ticking, hook firing, agent review)
