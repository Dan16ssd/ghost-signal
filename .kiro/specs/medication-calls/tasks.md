# Tasks: medicine reminder calls

- [x] 1. `meds.py`: time parsing (rules + AI), `next_due`, voices, call scripts (en, ar, th)
- [x] 2. Store: meds, doses, family tables; STOP stops meds
- [x] 3. MEDS / MEDS LIST / MEDS DEL / MEDS FAMILY / YES / 1 in `answer.handle`
- [x] 4. Dose loop: call, retry after 10 min, missed -> family SMS, SMS fallback, daily call cap
- [x] 5. Voice pages `/voice/dose/{id}`, `/voice/answer/{id}` with signature check
- [x] 6. Simulator: phone rings, Press 1 / Ignore, "MEDS in 1 min" demo buttons
- [x] 7. Tests incl. property test for `next_due` across time zones (`tests/test_meds.py`)
- [ ] 8. Enable Voice on the Twilio number; check voice names in the Twilio console
- [ ] 9. Danny listens to the Thai call as a Lao speaker; a Filipino speaker to the Tagalog call
- [ ] 10. Real call test from Laos and the Philippines; record it for the video
- [ ] 11. Check Twilio call prices to Laos and the Philippines; set GHOST_MAX_CALLS_PER_DAY
