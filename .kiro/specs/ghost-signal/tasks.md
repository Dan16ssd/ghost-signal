# Tasks: Ghost Signal

- [x] 1. SMS length rules (`sms.py`) with property tests
- [x] 2. Lao detection and fixed Lao/English messages (`lang.py`)
- [x] 3. Wikipedia + Open-Meteo sources (`sources.py`)
- [x] 4. Answer pipeline with AI and no-AI fallback (`answer.py`)
- [x] 5. Twilio webhook, signature check, background reply, rate limit (`app.py`, `twilio_sms.py`)
- [x] 6. Old-phone simulator page
- [ ] 7. Better Lao answers: when Lao Wikipedia has nothing, translate the question to English for search
- [ ] 8. Trusted health source (e.g. WHO fact sheets) for health questions
- [ ] 9. Deploy (public HTTPS URL), set `PUBLIC_BASE_URL`, connect the Twilio number
- [ ] 10. Kiro hook: run `python -m pytest -q` when a file in `ghost_signal/` is saved
- [ ] 11. Kiro MCP: add a server (e.g. fetch) and use it while building sources
- [ ] 12. Spooky polish for the simulator (Costume-quality design)
- [ ] 13. README write-up of how each Kiro feature was used (800+ words, screenshots)
