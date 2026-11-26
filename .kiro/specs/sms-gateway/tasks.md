# Tasks: SMS gateway

- [x] 1. `store.py` with opt-out, seen, hits, usage and reminders tables (in-memory DB in tests)
- [x] 2. STOP / START with local words; opted-out numbers get nothing (`tests/test_gateway.py`)
- [x] 3. Skip repeated MessageSid
- [x] 4. Hourly limit moved from memory to the store
- [x] 5. Daily AI budget with extract fallback
- [x] 6. Masked numbers in logs; `/health` usage numbers
- [ ] 7. Mounted volume (or Postgres) on the host so state survives redeploys
- [ ] 8. gateway-auditor agent run before the first public deploy
