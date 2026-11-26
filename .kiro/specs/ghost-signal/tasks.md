# Tasks: Ghost Signal

- [x] 1. SMS length rules (`sms.py`) with property tests
- [x] 2. Lao detection and fixed Lao/English messages (`lang.py`)
- [x] 3. Wikipedia + Open-Meteo sources (`sources.py`)
- [x] 4. Answer pipeline with AI and no-AI fallback (`answer.py`)
- [x] 5. Twilio webhook, signature check, background reply, rate limit (`app.py`, `twilio_sms.py`)
- [x] 6. Old-phone simulator page
- [x] 7. Translate the question to English for search when local Wikipedia has nothing
- [x] 7b. Arabic (Egypt): detection, messages, commands, Arabic city names
- [x] 7c. RATE command (ExchangeRate-API), local currency by language
- [x] 7e. Any country: calling code -> country/currency, 50+ languages, local Wikipedia,
      English retry, AI-translated fixed messages, simulator country picker
- [ ] 7d. Egyptian/Lao speakers check every fixed message for natural wording
- [ ] 8. Trusted health source (e.g. WHO fact sheets) for health questions
- [ ] 9. Deploy (public HTTPS URL), set `PUBLIC_BASE_URL`, connect the Twilio number
- [x] 10. Kiro hooks: tests on save, secret scan, HELP/README sync, language review
- [x] 11. Kiro MCP: Ghost Signal's own MCP server (`.kiro/specs/mcp-server`)
- [ ] 12. Spooky polish for the simulator (Costume-quality design)
- [ ] 13. README write-up of how each Kiro feature was used (800+ words, screenshots)
- [x] 14. Production pass: see specs `sms-gateway`, `reminders`, `phone-simulator`
- [x] 15. CI, Dockerfile, Render blueprint
