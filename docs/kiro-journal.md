# Build journal

An honest log of how Ghost Signal was built, for the judges and for us.

## How we work
- **Specs first.** Every feature has its own folder in `.kiro/specs/` (requirements in EARS
  form, design, tasks). We work task by task and tick tasks off in the same commit as the code.
- **Steering** (`.kiro/steering/`) holds the rules the agent must follow everywhere: product,
  tech, structure, SMS rules (length, STOP, privacy), languages and simulator design.
  The SMS, language and design files load only when matching files are open.
- **Hooks** (`.kiro/hooks/`): tests on save, secret and phone-number scan, HELP/README sync,
  and a language review whenever fixed messages change.
- **Custom agents** (`.kiro/agents/`): `language-reviewer` (Lao/Arabic wording and SMS length)
  and `gateway-auditor` (STOP, signatures, duplicates, cost caps, privacy) before deploys.
- **MCP**: Ghost Signal itself is an MCP server (`ghost_signal/mcp_server.py`). The agent and
  the hooks call `ask`, `check_sms` and `fixed_messages` to test real replies in any language
  without a phone.
- **Property-based tests** (Hypothesis) for the rules that must hold for every input.

## Log

### Nov 27 - first version (prepared before moving into Kiro)
- Repo skeleton, SMS length rules, Lao + English, Twilio webhook, simulator. The first spec
  (`ghost-signal`) and steering were drafted alongside. Property test found a crash on
  lone UTF-16 surrogates; fixed by counting units by hand.
- Arabic detection and messages, local city names for weather, RATE command.
- Any country: calling code -> country, language hint, currency; 54 languages; English retry
  when a small Wikipedia misses.

### Nov 27 - production pass
- Looked at what a production SMS service needs (and what other entries cover) and wrote
  four new specs: `sms-gateway`, `reminders`, `phone-simulator`, `mcp-server`.
- `sms-gateway`: STOP/START (local words too), one answer per Twilio MessageSid, hourly and
  daily-AI caps kept in SQLite, masked numbers, `/health` usage.
- `reminders`: REMIND in the sender's own time zone. **The property test caught a real bug**:
  on the New York spring daylight-saving day, "3am" asked at 2:33 gave a time in the past.
  Fixed by comparing real timestamps and adding "in N hours" in UTC.
- `phone-simulator`: multi-tap keypad, inbox for reminders, ghost + hint line, RTL Arabic.
- `mcp-server`: five tools, Kiro config with AI off.
- CI (GitHub Actions), Dockerfile, Render blueprint.

### Nov 27 - medicine calls (idea from Danny)
- New spec `medication-calls`: daily call, press 1, retry after 10 minutes, SMS to a family
  member who said YES. Lao has no Twilio voice, so Lao speakers hear Thai.
- Property test for `next_due` across four time zones; 80 tests in total.

### Nov 27 - one story: older people with old phones
- Looked at a natural-disaster story too, but chose one hero: an older person living alone
  with a basic phone. Medicine calls lead; ask-by-SMS and reminders support.
- Many languages, not one: hand-written call scripts in en, es, fr, pt, hi, tl, ar, th
  (Lao hears Thai), AI translation for the other voiced languages; Tagalog command words.

### Next, inside Kiro
- [ ] Run the `language-reviewer` agent on Lao and Arabic; Danny (Lao) and a Filipino speaker (Tagalog) confirm wording.
- [ ] Run `gateway-auditor` before the first deploy.
- [ ] Spec + tasks for the trusted health source (WHO), built task by task in Kiro.
- [ ] Spooky polish of the simulator with the design steering.
- [ ] Screenshots of specs, hooks firing and MCP tools for the README and video.
