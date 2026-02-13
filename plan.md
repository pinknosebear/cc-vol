# Plan: Volunteer Scheduling System (cc-vol)

## Context

Replace WhatsApp group chat + Google Sheet signup process for daily volunteer
shift scheduling at a Sai Baba Temple. ~50 volunteers, 2-3 coordinators.
Daily shifts: 1 Kakad + 1 Robe (variable capacity by day of week).
Two-phase signup period before the month, then unrestricted mid-month pickup. Coordinators need visibility into gaps and tools to find
substitutes. System must minimize friction and reduce WhatsApp group noise.

Architecture: FastAPI (Python) + SQLite + Node.js WhatsApp bridge (Baileys).
Two-process design — all business logic in Python, thin WA relay in Node.
WhatsApp identity only for MVP (phone number = identity via Baileys, not Business API).

Isolation principle: every task has exactly one reason to fail. If a test breaks,
the agent knows what broke without chasing phantom failures in adjacent code.

See .tt/decisions.md for design decision log.
See .tt/archive/plan-v1-initial.md for original plan before revisions.

---

## Phase 1: Domain Models

Define the data structures, schema, and Pydantic models. No business logic, no
seed data, no API. Just the foundation that everything else builds on.

Each model task delivers: SQLite table DDL, Pydantic model, basic CRUD functions
(insert, get_by_id, list), and a pytest fixture that creates the table in an
in-memory DB.

### p1-01: Volunteer domain model

priority: 100
phase: phase-1
tags: backend, domain
scope: app/models/volunteer.py, app/db.py, tests/conftest.py

Table: `volunteers`
- id (INTEGER PRIMARY KEY)
- phone (TEXT UNIQUE NOT NULL) — WhatsApp number, serves as identity
- name (TEXT NOT NULL)
- is_coordinator (BOOLEAN DEFAULT FALSE)
- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

Pydantic models:
- VolunteerCreate(phone, name, is_coordinator=False)
- Volunteer(id, phone, name, is_coordinator, created_at)

CRUD:
- create_volunteer(db, data) → Volunteer
- get_volunteer_by_phone(db, phone) → Volunteer | None
- list_volunteers(db) → list[Volunteer]

Fixture: `db` — in-memory SQLite with all tables created. Shared across test files.

### p1-02: Shift domain model

priority: 95
phase: phase-1
tags: backend, domain
scope: app/models/shift.py

Table: `shifts`
- id (INTEGER PRIMARY KEY)
- date (DATE NOT NULL)
- type (TEXT NOT NULL CHECK type IN ('kakad', 'robe'))
- capacity (INTEGER NOT NULL)
- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- UNIQUE(date, type) — one row per type per day

Note: 2 rows per day (1 Kakad + 1 Robe). Capacity varies by day of week:
- Kakad: always capacity 1
- Robe: capacity 3 on Sun/Mon/Wed/Fri, capacity 4 on Tue/Thu/Sat
Multiple volunteers sign up for the same shift_id. Capacity check =
count active signups < shift.capacity. (See decision D10)

Pydantic models:
- ShiftCreate(date, type, capacity)
- Shift(id, date, type, capacity, created_at)

CRUD:
- create_shift(db, data) → Shift
- get_shifts_by_date(db, date) → list[Shift]
- get_shifts_by_month(db, year, month) → list[Shift]

### p1-03: Signup domain model

depends-on: p1-01, p1-02
priority: 90
phase: phase-1
tags: backend, domain
scope: app/models/signup.py

Table: `signups`
- id (INTEGER PRIMARY KEY)
- volunteer_id (INTEGER NOT NULL REFERENCES volunteers(id))
- shift_id (INTEGER NOT NULL REFERENCES shifts(id))
- signed_up_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- dropped_at (TIMESTAMP NULL) — soft delete for drops
- UNIQUE(volunteer_id, shift_id)

Pydantic models:
- SignupCreate(volunteer_id, shift_id)
- Signup(id, volunteer_id, shift_id, signed_up_at, dropped_at)

CRUD:
- create_signup(db, data) → Signup
- drop_signup(db, signup_id) → Signup (sets dropped_at)
- get_signups_by_volunteer(db, volunteer_id, month) → list[Signup]
- get_signups_by_shift(db, shift_id) → list[Signup]
- get_active_signups_by_shift(db, shift_id) → list[Signup] (where dropped_at IS NULL)

Note: This is JUST the data layer. No rule validation here — that's the rules
engine's job. create_signup inserts the row; the rules engine decides whether
to call create_signup.

---

## Phase 2: Seed Data & Rules Engine

Three parallel tracks, then they converge.

Track A (seeds): p2-01, p2-02
Track B (rules pure): p2-03 → p2-04
Track C (rules queries): p2-05 → p2-06
Then: p2-07 → p2-08
Then: p2-09 → p2-10 + p2-11

### p2-01: Seed monthly shift data

depends-on: p1-02
priority: 85
phase: phase-2
tags: backend, seed
scope: app/seed.py, tests/test_seed.py

Function: seed_month(db, year, month)
- For each day in the month: insert 1 Kakad + 1 Robe shift
- Kakad capacity = 1 always
- Robe capacity = 3 on Sun/Mon/Wed/Fri, 4 on Tue/Thu/Sat
- Helper: get_robe_capacity(weekday) → 3 or 4
- Idempotent — skip if shifts already exist for that date
- Returns count of shifts created

Test: seed February 2026, verify 28 * 2 = 56 shifts. Run twice, verify no dupes.
Verify Robe capacity: Feb 1 2026 = Sunday → capacity 3, Feb 3 = Tuesday → capacity 4.

### p2-02: Seed dummy volunteer profiles

depends-on: p1-01
priority: 85
phase: phase-2
tags: backend, seed
scope: app/seed.py

Function: seed_volunteers(db)
- 10 volunteers with varied profiles:
  - 2 coordinators
  - 3 "active" volunteers (will have many signups)
  - 3 "occasional" volunteers (1-2 signups)
  - 2 "new" volunteers (no signups yet)
- Deterministic — same names/phones every run for reproducibility
- Idempotent — skip if phone already exists

### p2-03: Pure validation rule functions

depends-on: p1-03
priority: 88
phase: phase-2
tags: backend, rules
scope: app/rules/pure.py

Pure functions with no DB dependency. All phase-aware (see decision D11).

SignupPhase enum: PHASE_1, PHASE_2, MID_MONTH

Phase determination:
- get_signup_phase(today, shift_month_start) → SignupPhase
  - 2+ weeks before month start → PHASE_1
  - 1-2 weeks before month start → PHASE_2
  - On or after month start → MID_MONTH

Phase 1 rules (2 weeks before):
- check_kakad_limit(kakad_count, max=2) → RuleResult
- check_robe_limit(robe_count, max=4) → RuleResult
- check_thursday_limit(thursday_count, max=1) → RuleResult
- check_phase1_total(total_count, max=6) → RuleResult
  Note: Kakad and Robe caps are independent. 2K + 4R = 6 max.

Phase 2 rules (1 week before):
- check_phase2_additional(phase2_count, max=2) → RuleResult
- check_running_total(total_count, max=8) → RuleResult
  Note: No per-type or Thursday restrictions in Phase 2.

Always checked:
- check_capacity(current_signups, capacity) → RuleResult

Mid-month: no rules checked (except capacity).

Helper:
- get_applicable_rules(phase) → list of rule check functions

RuleResult = namedtuple('RuleResult', ['allowed', 'reason'])

One failure mode: logic error in a pure function.

### p2-04: Test pure validation rules

depends-on: p2-03
priority: 87
phase: phase-2
tags: testing
scope: tests/test_rules_pure.py

Tests with hardcoded inputs — no DB, no fixtures:

Phase determination:
- 15 days before → PHASE_1
- 7 days before → PHASE_2
- Day of month start → MID_MONTH
- Boundary: exactly 14 days before → PHASE_1
- Boundary: exactly 7 days before → PHASE_2

Phase 1 checks:
- check_kakad_limit(1, 2) → allowed
- check_kakad_limit(2, 2) → rejected
- check_robe_limit(3, 4) → allowed
- check_robe_limit(4, 4) → rejected
- check_thursday_limit(0, 1) → allowed
- check_thursday_limit(1, 1) → rejected
- check_phase1_total(5, 6) → allowed
- check_phase1_total(6, 6) → rejected

Phase 2 checks:
- check_phase2_additional(1, 2) → allowed
- check_phase2_additional(2, 2) → rejected
- check_running_total(7, 8) → allowed
- check_running_total(8, 8) → rejected

Capacity:
- check_capacity(0, 1) → allowed
- check_capacity(1, 1) → rejected (full)
- check_capacity(2, 3) → allowed
- check_capacity(3, 3) → rejected

get_applicable_rules:
- PHASE_1 returns Phase 1 rule set
- PHASE_2 returns Phase 2 rule set
- MID_MONTH returns empty (only capacity)

One failure mode: pure logic doesn't match spec.

### p2-05: DB query layer for rule counts

depends-on: p2-03
priority: 86
phase: phase-2
tags: backend, rules
scope: app/rules/queries.py

Functions that query signup counts from the DB:
- get_kakad_count(db, volunteer_id, month) → int
- get_robe_count(db, volunteer_id, month) → int
- get_total_count(db, volunteer_id, month) → int
- get_thursday_count(db, volunteer_id, month) → int
- get_phase2_count(db, volunteer_id, month) → int
  (signups created during Phase 2 window — needs signed_up_at comparison)
- get_shift_signup_count(db, shift_id) → int
- get_shift_capacity(db, shift_id) → int

Uses signup and shift models. Returns ints only.
Excludes dropped signups (dropped_at IS NOT NULL).

One failure mode: query returns wrong count.

### p2-06: Test query layer with in-memory DB

depends-on: p2-05
priority: 85
phase: phase-2
tags: testing
scope: tests/test_rules_queries.py

Setup: create volunteer, shifts, signups in test DB fixture.
Assert counts match expected:
- 2 kakad signups → get_kakad_count = 2
- 3 robe signups → get_robe_count = 3
- 2 kakad + 3 robe → get_total_count = 5
- 1 thursday signup → get_thursday_count = 1
- dropped signup not counted in any query
- shift with 2 signups → get_shift_signup_count = 2
- get_phase2_count: signups with signed_up_at in Phase 2 window only

One failure mode: query filters/joins wrong.

### p2-07: Signup validation orchestrator

depends-on: p2-05, p2-04
priority: 84
phase: phase-2
tags: backend, rules
scope: app/rules/validator.py

Combines queries + pure rules into one function:
- validate_signup(db, volunteer_id, shift_id, today=None) → list[RuleResult]

Steps:
1. Get shift details: month, date, type, capacity, day_of_week
2. Determine phase: get_signup_phase(today, shift_month_start)
3. If MID_MONTH: only check capacity
4. Get all counts from query layer
5. Get applicable rules for phase via get_applicable_rules(phase)
6. Run each rule with appropriate counts
7. Always check capacity regardless of phase
8. Return list of all rule violations (empty = allowed)

The validator MUST pass `today` to get_signup_phase so tests can
control the current date. Default to date.today() in production.

One failure mode: orchestration error (wrong param passed to pure fn).

### p2-08: Integration test for validator

depends-on: p2-07
priority: 83
phase: phase-2
tags: testing
scope: tests/test_rules_validator.py

End-to-end tests with test DB. Each test sets today= to control phase.

Phase 1 scenarios (today = 2+ weeks before month):
- 2 kakad already → 3rd kakad → rejected "kakad limit"
- 4 robe already → 5th robe → rejected "robe limit"
- 1 thursday already → 2nd thursday → rejected "thursday limit"
- 6 total (2K+4R) → 7th → rejected "phase 1 total"
- Same-day Kakad + Robe → allowed (independent caps)

Phase 2 scenarios (today = 1 week before month):
- 6 from Phase 1, 0 Phase 2 → allowed (Phase 2 +2 available)
- 6 from Phase 1, 2 Phase 2 → rejected "phase 2 additional limit"
- 8 total → rejected "running total"
- Thursday OK in Phase 2 (no Thursday restriction)

Always:
- Shift at capacity → rejected "capacity"
- Mid-month → all rules bypassed (only capacity checked)
- Drop a shift, re-sign → allowed (dropped doesn't count)
- Month boundary: Jan signups don't count against Feb
- Fresh volunteer, open shift → all valid

One failure mode: validator doesn't integrate queries + rules correctly.

### p2-09: Seed signups with crafted scenarios

depends-on: p2-01, p2-02, p2-07
priority: 80
phase: phase-2
tags: backend, seed
scope: app/seed.py

Function: seed_signups(db, year, month)
- Uses the rules engine to create signups (not raw inserts)
- Must pass today= to validator to simulate Phase 1 / Phase 2 timing
- Crafted to produce interesting query results:
  - Volunteer A: 2 Kakad + 4 Robe (at Phase 1 max = 6)
  - Volunteer B: 1 Thursday shift (at Thursday limit)
  - Volunteer C: 6 from Phase 1 + 2 from Phase 2 (at running total = 8)
  - Volunteer D: signed up then dropped one
  - Volunteer E: 1 shift only (light user)
  - Leave some shifts completely empty (for coordinator gap queries)
  - Leave some days fully staffed (for contrast)
- Returns dict of created signups by volunteer for downstream verification
- Idempotent — skip if signups already exist for the volunteer-month pair

This task succeeds if all valid signups are inserted. No assertion testing here.

### p2-10: Verify seeded signup state

depends-on: p2-09
priority: 79
phase: phase-2
tags: testing, seed
scope: tests/test_seed_signups.py

Queries the seeded DB and asserts expected state:
- Volunteer A has exactly 2 Kakad + 4 Robe active signups (Phase 1 max)
- Volunteer B has exactly 1 Thursday shift
- Volunteer C has 6 Phase 1 + 2 Phase 2 = 8 total (running total max)
- Volunteer D has 1 dropped signup + active ones
- Volunteer E has exactly 1 shift
- Specific shifts are empty (by shift_id)
- Specific days are fully staffed

One failure mode: the seed data was wrong or incomplete.

### p2-11: Test expected rule rejections with seeded data

depends-on: p2-09
priority: 78
phase: phase-2
tags: testing, rules
scope: tests/test_rules_rejections.py

Integration tests for rule violations using seeded data:

Phase 1 rejections (today = 2+ weeks before):
- Volunteer A (2K+4R=6) tries another Kakad → rejected "kakad limit"
- Volunteer A (2K+4R=6) tries another Robe → rejected "robe limit"
- Volunteer A (2K+4R=6) tries anything → rejected "phase 1 total"
- Volunteer B (1 Thursday) tries 2nd Thursday → rejected "thursday limit"

Phase 2 rejections (today = 1 week before):
- Volunteer C (8 total) tries 9th → rejected "running total"

Always:
- Try to sign up for full shift → rejected with "capacity" reason

One failure mode: rules engine doesn't reject when it should with real data.

---

## Phase 3: API & WhatsApp Bridge

Three parallel tracks.

Track A: p3-01 → p3-02..p3-09 (API endpoints, each isolated)
Track B: p3-10 (WhatsApp bridge, fully independent)
Track C: p3-11, p3-12 → p3-13..p3-16 → p3-17 (bot layer)

### p3-01: FastAPI app skeleton

depends-on: p2-09
priority: 75
phase: phase-3
tags: backend, api
scope: app/main.py

FastAPI() instance, CORS, DB connection lifecycle, /healthz endpoint.
No business endpoints — just the mountable app that other tasks register routes into.

Test: GET /healthz returns 200.

One failure mode: app won't start.

### p3-02: GET /api/shifts (month view)

depends-on: p3-01
priority: 74
phase: phase-3
tags: backend, api
scope: app/routes/shifts.py, tests/test_api_list_shifts.py

GET /api/shifts?month=YYYY-MM
Returns: list of shifts in month with signup_count, capacity.

Tests:
- Valid month returns shifts with counts
- Invalid month format returns 400

One failure mode: query/serialization for shift list.

### p3-03: GET /api/shifts/{date} (day detail)

depends-on: p3-01
priority: 73
phase: phase-3
tags: backend, api
scope: app/routes/shifts.py, tests/test_api_day_detail.py

GET /api/shifts/{date}
Returns: shifts for that day with array of signed-up volunteers.

Tests:
- Valid date returns shifts + volunteer list
- Date with no shifts returns empty array
- Invalid date format returns 400

One failure mode: join query or response shape for day view.

### p3-04: POST /api/signups

depends-on: p3-01, p2-07
priority: 72
phase: phase-3
tags: backend, api
scope: app/routes/signups.py, tests/test_api_create_signup.py

POST /api/signups {volunteer_phone, shift_id}
Validates via rules engine. 422 with violation reasons on failure. 201 on success.

Tests:
- Valid signup succeeds (201)
- Rule violation returns 422 with clear message
- Nonexistent shift_id returns 404
- Nonexistent volunteer_phone returns 404
- Duplicate signup returns 409

One failure mode: rules integration or error response formatting.

### p3-05: DELETE /api/signups/{id}

depends-on: p3-01
priority: 71
phase: phase-3
tags: backend, api
scope: app/routes/signups.py, tests/test_api_drop_signup.py

DELETE /api/signups/{id}
Sets dropped_at. Returns 204 on success.

Tests:
- Valid drop succeeds, sets dropped_at
- Already dropped returns 404
- Nonexistent signup_id returns 404

One failure mode: soft delete logic.

### p3-06: GET /api/volunteers/{phone}/shifts

depends-on: p3-01
priority: 70
phase: phase-3
tags: backend, api
scope: app/routes/volunteers.py, tests/test_api_my_shifts.py

GET /api/volunteers/{phone}/shifts
Returns: upcoming shifts for volunteer (dropped_at IS NULL).

Tests:
- Valid phone returns upcoming shifts
- Phone with no shifts returns empty array
- Dropped shifts not included

One failure mode: volunteer-specific shift query.

### p3-07: GET /api/coordinator/status

depends-on: p3-01
priority: 68
phase: phase-3
tags: backend, api, coordinator
scope: app/routes/coordinator.py, tests/test_api_coord_status.py

GET /api/coordinator/status?date=YYYY-MM-DD
Returns: shifts with fill status (capacity, signup_count, filled/open).

Tests:
- Returns shifts with correct fill calculations
- Missing date defaults to today
- Invalid date returns 400

One failure mode: fill status calculation.

### p3-08: GET /api/coordinator/gaps

depends-on: p3-01
priority: 67
phase: phase-3
tags: backend, api, coordinator
scope: app/routes/coordinator.py, tests/test_api_coord_gaps.py

GET /api/coordinator/gaps?month=YYYY-MM
Returns: shifts where signup_count < capacity.

Tests:
- Returns only unfilled shifts
- Fully filled shifts excluded
- Correct gap_size calculation

One failure mode: gap detection query.

### p3-09: GET /api/coordinator/volunteers/available

depends-on: p3-01, p2-07
priority: 66
phase: phase-3
tags: backend, api, coordinator
scope: app/routes/coordinator.py, tests/test_api_coord_available.py

GET /api/coordinator/volunteers/available?date=YYYY-MM-DD
Returns: volunteers who haven't hit limits for that month.

Tests:
- Returns volunteers under their limit
- Excludes volunteers at/over limit

One failure mode: available-volunteers query using rules engine.

### p3-10: Node.js WhatsApp bridge with Baileys

priority: 65
phase: phase-3
tags: whatsapp, bridge
scope: wa-bridge/

Minimal Node.js service using @whiskeysockets/baileys:
- Connect to WhatsApp via QR code scan
- Persist session to disk (no re-scan on restart)
- HTTP API: POST /send {phone, message} — send a message
- Webhook: forward incoming messages to FastAPI POST /api/wa/incoming
- Health check: GET /health
- Graceful reconnect on disconnect

Standalone service. Communicates with FastAPI over HTTP only.
Can be developed and tested independently of the Python backend.

### p3-11: Message pattern matcher and command extractor

depends-on: p3-01
priority: 62
phase: phase-3
tags: backend, whatsapp, parser
scope: app/bot/parser.py, tests/test_bot_parser.py

Pure function layer — no DB, no API calls, just pattern matching.

Input: raw message string
Output: ParsedCommand(command_type, args) or ParseError(original, suggestions)

Patterns:
- "signup <date> <type>" → ParsedCommand("signup", {date, type})
- "drop <date> <type>" → ParsedCommand("drop", {date, type})
- "my shifts" → ParsedCommand("my_shifts", {})
- "shifts <date>" → ParsedCommand("shifts", {date})
- "status <date>" → ParsedCommand("status", {date})
- "gaps" → ParsedCommand("gaps", {})
- "find sub <date> <type>" → ParsedCommand("find_sub", {date, type})
- "help" → ParsedCommand("help", {})
- Unknown → ParseError with suggestions

Fuzzy matching: "singup" suggests "signup".
Date parsing: "today", "tomorrow", "2026-03-15", "15 March".

Tests: unit tests with strings in, ParsedCommand/ParseError out. No HTTP.
One failure mode: pattern doesn't match or date parse fails.

### p3-12: Phone-based volunteer context lookup

depends-on: p1-01
priority: 61
phase: phase-3
tags: backend, whatsapp, auth
scope: app/bot/auth.py, tests/test_bot_auth.py

Function: get_volunteer_context(db, phone) → VolunteerContext | None

VolunteerContext(volunteer_id, phone, is_coordinator)

This is the ONLY place that checks is_coordinator. Command handlers receive
VolunteerContext as input and assume it's validated.

Tests:
- Coordinator phone → is_coordinator=True
- Volunteer phone → is_coordinator=False
- Unknown phone → None

One failure mode: phone lookup or coordinator flag wrong.

### p3-13: Volunteer signup command handler

depends-on: p3-11, p3-12, p3-04
priority: 58
phase: phase-3
tags: backend, whatsapp
scope: app/bot/handlers/volunteer.py, tests/test_bot_vol_signup.py

Handler: handle_signup(db, context, args) → str (WhatsApp message)

Calls create signup logic. Returns human-readable success or violation message.

Tests: mock rules responses, verify message formatting.
One failure mode: signup handler formatting or API call.

### p3-14: Volunteer drop command handler

depends-on: p3-11, p3-12, p3-05
priority: 57
phase: phase-3
tags: backend, whatsapp
scope: app/bot/handlers/volunteer.py, tests/test_bot_vol_drop.py

Handler: handle_drop(db, context, args) → str

Finds signup matching volunteer+date+type, drops it.

Tests: existing signup → success msg, no match → error msg, already dropped → error msg.
One failure mode: shift lookup or drop logic.

### p3-15: Volunteer query command handlers (my shifts + shifts)

depends-on: p3-11, p3-12, p3-06, p3-02
priority: 56
phase: phase-3
tags: backend, whatsapp
scope: app/bot/handlers/volunteer.py, tests/test_bot_vol_query.py

Handlers:
- handle_my_shifts(db, context) → str
- handle_shifts(db, context, args) → str

Read-only queries formatted as WhatsApp messages.

Tests: 0 shifts, 1 shift, many shifts, empty day.
One failure mode: message formatting for shift lists.

### p3-16: Coordinator command handlers

depends-on: p3-11, p3-12, p3-07, p3-08, p3-09
priority: 54
phase: phase-3
tags: backend, whatsapp, coordinator
scope: app/bot/handlers/coordinator.py, tests/test_bot_coord.py

Handlers:
- handle_status(db, context, args) → str
- handle_gaps(db, context, args) → str
- handle_find_sub(db, context, args) → str

All require context.is_coordinator == True (caller checks this).
Format coordinator data as WhatsApp messages.

Tests: mock API responses, verify formatting.
One failure mode: coordinator message formatting.

### p3-17: Route parsed commands to handlers

depends-on: p3-11, p3-12, p3-13, p3-14, p3-15, p3-16
priority: 50
phase: phase-3
tags: backend, whatsapp
scope: app/routes/wa_incoming.py, tests/test_bot_dispatcher.py

POST /api/wa/incoming receives {phone, message} from wa-bridge.

Flow:
1. get_volunteer_context(phone) → None? → "Phone not registered."
2. parse_message(message) → ParseError? → return suggestions
3. Coordinator command + not coordinator? → "That's for coordinators only."
4. Route to correct handler
5. Return response string

Tests:
- Unknown phone → registration message
- Parse error → suggestions
- Volunteer tries coord command → denied
- Each command type routed correctly

One failure mode: routing or permission gating logic.

---

## Verification

- **Phase 1**: `pytest` — model fixtures create tables, CRUD works, constraints enforced.
- **Phase 2**: `pytest` — pure rule tests pass, query tests pass, validator tests pass, seed verified, rejections confirmed.
- **Phase 3**: `pytest` — each endpoint tested individually. Bot parser tested with strings. Dispatcher routing verified. `curl` endpoints with seeded data. WhatsApp message → correct response.

---

## Future Phases (not yet scoped)

- **Phase 4: Web View** — phone-based lookup, volunteer shift view, coordinator dashboard
- **Phase 5: Notifications & Escalation** — reminders, ack handling, empty slot alerts, seniority escalation
