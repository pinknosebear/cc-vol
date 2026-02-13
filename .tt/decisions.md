# Design Decisions Log

## D1: Merge project setup into first real task
**Date:** 2026-02-13
**Context:** p1-t1 (project setup) was just mkdirs and a requirements.txt — not a real task.
**Decision:** Absorb setup into the first domain model tasks. No standalone scaffolding task.
**Impact:** Removed p1-t1 as a bottleneck. vol-model and shift-model can start in parallel.

## D2: Domain models over database tables
**Date:** 2026-02-13
**Context:** Original p1-t2 was "define SQLite schema" — one task for all tables.
**Options considered:**
- `db-*` (one task per table) — boundaries cut across actual usage, trivial tests, merge conflicts in shared files
- `*-model` (one task per domain concept) — vertical slice: table + Pydantic + queries + fixtures per task
**Decision:** `*-model` approach. Each task owns a full vertical slice. Better for parallel agents, meaningful tests, and clean ownership.
**Impact:** Replaced p1-t2 with vol-model, shift-model, signup-model.

## D3: Signup model absorbs rules engine
**Date:** 2026-02-13
**Context:** Original plan had p1-t3 (rules engine) separate from the signup model.
**Decision:** Merge into signup-model. You can't write a meaningful signup create without rules — they're the same domain concept.
**Impact:** signup-model = table + Pydantic + rules + validation. Tighter, more testable unit.

## D4: Seed script absorbed into shift-model
**Date:** 2026-02-13
**Context:** Original p1-t5 (seed monthly shift data) was standalone.
**Decision:** Monthly seed is just "generate rows in shifts table" — belongs with the shift domain model.
**Impact:** Removed p1-t5 as separate task.

## D5: Notifications moved to post-MVP
**Date:** 2026-02-13
**Context:** Original plan had notifications in Phase 2-3 (reminders, ack, escalation).
**Decision:** Notifications are purely additive. MVP = signups + coordinator visibility. Pull all notification work (notif-model, reminders, ack handling, escalation) to Phase 5.
**Impact:** Smaller MVP. Phases 3-4 can ship without notification infrastructure.

## D6: Web view added before notifications
**Date:** 2026-02-13
**Context:** No web interface in original plan. Discussed auth approach.
**Options considered:**
- WhatsApp-only identity (phone = identity, no auth needed)
- Phone + PIN (lightweight web auth)
- Full user accounts (overkill)
**Decision:** WhatsApp-only for MVP. Add web view (phone-based lookup) as Phase 4, before notifications (Phase 5). Gives volunteers and coordinators a visual interface without texting.
**Impact:** New Phase 4. Notifications pushed to Phase 5.

## D7: Baileys, not WhatsApp Business API
**Date:** 2026-02-13
**Context:** Confirmed using @whiskeysockets/baileys (unofficial WA Web client via QR scan), not the official Business API.
**Rationale:** No Meta approval needed, free, sufficient for small volunteer group. Accepted risk: Meta can break it, technically against ToS, session can get logged out.
**Impact:** No cost, no approval process, but fragile long-term.

## D8: Reverted D3 — rules engine separate from signup model
**Date:** 2026-02-13
**Context:** D3 merged rules into signup-model. On further discussion, signup-model is the data layer (table + CRUD), and the rules engine is business logic that operates ON that data. They have different testing needs.
**Decision:** Keep them separate. signup-model = pure data (Phase 1). rules-engine = pure logic + DB-aware wrapper (Phase 2). Rules engine depends on signup-model, not the other way around.
**Rationale:**
- Rules engine Layer 1 (pure functions) needs NO database at all — just pass in counts
- Rules engine Layer 2 (DB wrapper) needs the models but tests with in-memory fixtures
- Seed signups run THROUGH the rules engine, serving as integration test
- This means Phase 1 has zero business logic — just structure. Clean separation.
**Impact:** signup-model back to data-only. rules-engine is its own Phase 2 task.

## D9: Two-track Phase 2 — seeds parallel with rules
**Date:** 2026-02-13
**Context:** Seed data (shifts, volunteers) and the rules engine don't depend on each other. They converge at seed-signups.
**Decision:** Phase 2 has two parallel tracks:
- Track A: seed-shifts + seed-volunteers (data population)
- Track B: rules-engine + rules-tests (business logic)
- Convergence: seed-signups runs signups through rules, both seeding data AND integration testing.
**Impact:** More parallelism in Phase 2. seed-signups becomes both a seed script and a proof that rules + models work together.

## D10: Single shift row with variable capacity (not 1:1 slot rows)
**Date:** 2026-02-13
**Context:** Original plan had 5 rows per day (1 Kakad + 4 Robe slots). But Robe capacity varies by day of week.
**Decision:** 2 rows per day: 1 Kakad (capacity 1), 1 Robe (capacity varies).
- Sun/Mon/Wed/Fri: Robe capacity = 3
- Tue/Thu/Sat: Robe capacity = 4
Multiple volunteers sign up for the same shift_id. UNIQUE(volunteer_id, shift_id) prevents double signup. Capacity check = count active signups < capacity.
**Impact:** Simpler schema, fewer rows, no slot_number needed. UNIQUE constraint changes from UNIQUE(date, type, capacity) to UNIQUE(date, type).

## D11: Two-phase signup period with revised limits
**Date:** 2026-02-13
**Context:** Original plan had single signup period with max 4 total. Actual process is more nuanced.
**Corrected rules from domain expert:**

Phase 1 — 2 weeks before the month:
- Max 2 Kakad per volunteer (independent cap)
- Max 4 Robe per volunteer (independent cap)
- Max 1 Thursday per volunteer
- Total from Phase 1: up to 6 (2K + 4R)

Phase 2 — 1 week before the month:
- +2 additional slots, any type
- No Thursday restriction
- No type restriction
- Running total: up to 8

Mid-month pickup (after month starts):
- No limits at all

**Impact:** Rules engine needs signup_phase concept. Pure functions need to know which phase to apply. Significantly more complex than original "max 4 total" plan. The `is_signup_period` function becomes `get_signup_phase(date, shift_month) → Phase1 | Phase2 | MidMonth`.
