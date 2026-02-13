# Plan: Volunteer Scheduling System (cc-vol)

## Context

Replace WhatsApp group chat + Google Sheet signup process for daily volunteer
shift scheduling at a Sai Baba Temple. ~50 volunteers, 2-3 coordinators.
Daily shifts: 1 Kakad + 4 Robe. Volunteers sign up last week of previous month
with rule enforcement. Coordinators need visibility into gaps and tools to find
substitutes. System must minimize friction and reduce WhatsApp group noise.

Architecture: FastAPI (Python) + SQLite + Node.js WhatsApp bridge (Baileys).
Two-process design — all business logic in Python, thin WA relay in Node.

---

## Phase 1: Data Model & Signup Rules Engine

### p1-t1: Initialize project structure and dependencies

priority: 100
phase: phase-1
tags: setup, backend

Set up Python project with FastAPI, SQLite, pytest. Create directory structure:
```
cc-vol/
├── app/
│   ├── main.py          # FastAPI app entry
│   ├── db.py            # SQLite connection + schema init
│   ├── models.py        # Pydantic models
│   ├── routes/          # API route modules
│   └── rules.py         # Signup rule engine
├── tests/
├── wa-bridge/           # Node.js WhatsApp bridge (Phase 2)
├── requirements.txt
└── plan.md
```

### p1-t2: Define SQLite schema and database layer

depends-on: p1-t1
priority: 95
phase: phase-1
tags: db, backend

Tables:
- `volunteers` (id, phone, name, is_coordinator, created_at)
- `shifts` (id, date, type [kakad|robe], capacity, created_at)
- `signups` (id, volunteer_id, shift_id, signed_up_at, dropped_at)
- `notifications` (id, volunteer_id, shift_id, type, scheduled_for, sent_at, channel)

Schema enforces: unique signup per volunteer per shift, foreign keys.
Write migration/init script that creates tables on first run.

### p1-t3: Implement signup rules engine

depends-on: p1-t2
priority: 90
phase: phase-1
tags: backend, rules

Rules enforced during signup period (last week of previous month):
- Max 2 Kakad shifts per volunteer per month
- Max 4 total shifts per volunteer per month
- Max 2 Thursday shifts per volunteer per month
- Shift capacity limits (1 for Kakad, 4 for Robe)
- Can sign up for Kakad AND Robe on same day

Rules NOT enforced for mid-month pickups (after month starts).
Engine returns clear error messages for each violated rule.
Pure functions, no side effects — fully unit testable.

### p1-t4: API routes for shifts and signups

depends-on: p1-t3
priority: 85
phase: phase-1
tags: backend, api

Endpoints:
- `GET /api/shifts?month=YYYY-MM` — list shifts for a month
- `GET /api/shifts/{date}` — shifts for a specific day
- `POST /api/signups` — sign up (validates rules)
- `DELETE /api/signups/{id}` — drop a shift
- `GET /api/volunteers/{phone}/shifts` — my upcoming shifts

### p1-t5: Seed monthly shift data

depends-on: p1-t2
priority: 80
phase: phase-1
tags: backend, db

Script/endpoint to generate all shifts for a given month:
- For each day: 1 Kakad shift (capacity 1) + 4 Robe shifts (capacity 1 each)
- Idempotent — running twice for same month is safe

### p1-t6: Unit tests for signup rules

depends-on: p1-t3
priority: 75
phase: phase-1
tags: testing

Test each rule independently:
- Kakad limit (2/month)
- Total shift limit (4/month)
- Thursday limit (2/month)
- Capacity enforcement
- Same-day Kakad+Robe allowed
- Mid-month pickup bypasses all rules
- Edge cases: month boundaries, dropping and re-signing

---

## Phase 2: WhatsApp Bridge & Bot Commands

### p2-t1: Set up Node.js WhatsApp bridge with Baileys

depends-on: p1-t1
priority: 70
phase: phase-2
tags: whatsapp, bridge

Minimal Node.js service using @whiskeysockets/baileys:
- Connect to WhatsApp via QR code scan
- Persist session to disk (no re-scan on restart)
- HTTP API: `POST /send` (phone, message) and webhook for incoming messages
- Forward incoming messages to FastAPI `POST /api/wa/incoming`
- Health check endpoint

### p2-t2: Bot command parser

depends-on: p2-t1, p1-t4
priority: 65
phase: phase-2
tags: backend, whatsapp

Parse WhatsApp messages into commands:
- `signup <date> <type>` — sign up for a shift
- `drop <date> <type>` — drop a shift
- `my shifts` — list upcoming shifts
- `shifts <date>` — show available shifts for a date
- `help` — list commands

Return human-readable responses. Handle typos gracefully.

### p2-t3: Notification service abstraction

depends-on: p1-t2
priority: 60
phase: phase-2
tags: backend, notifications

Abstract notification interface:
```python
class NotificationChannel(Protocol):
    async def send(self, phone: str, message: str) -> bool: ...
```

Implementations:
- `WhatsAppChannel` — calls WA bridge HTTP API
- `LogChannel` — prints to console (for dev/testing)

Notification scheduler reads from `notifications` table, sends via configured channel.

---

## Phase 3: Automated Reminders

### p3-t1: Reminder scheduling logic

depends-on: p2-t3, p1-t4
priority: 55
phase: phase-3
tags: backend, notifications

When a volunteer signs up, schedule two notification rows:
- 7 days before shift
- 1 day before shift

Background task (APScheduler or simple loop) checks `notifications` table
every hour, sends unsent notifications whose `scheduled_for` has passed.

### p3-t2: Acknowledgement handling

depends-on: p3-t1, p2-t2
priority: 50
phase: phase-3
tags: backend, whatsapp

After receiving a reminder, volunteer can reply:
- `confirm` — mark shift as confirmed
- `drop` — drop the shift, trigger empty slot flow

Add `confirmed_at` column to signups table.

---

## Phase 4: Coordinator Tools

### p4-t1: Coordinator status dashboard (API)

depends-on: p1-t4
priority: 45
phase: phase-4
tags: backend, api, coordinator

Endpoints for coordinators:
- `GET /api/coordinator/status?date=YYYY-MM-DD` — shifts with fill status
- `GET /api/coordinator/gaps?month=YYYY-MM` — all unfilled shifts
- `GET /api/coordinator/volunteers/available?date=YYYY-MM-DD` — who hasn't hit limits

### p4-t2: Coordinator bot commands

depends-on: p4-t1, p2-t2
priority: 40
phase: phase-4
tags: whatsapp, coordinator

Commands (coordinator-only, checked by phone number):
- `status <date>` — who's signed up, what's empty
- `gaps` — list all unfilled upcoming shifts
- `find sub <date> <type>` — list available volunteers for a shift

### p4-t3: Empty slot group notification

depends-on: p4-t1, p2-t3
priority: 35
phase: phase-4
tags: whatsapp, notifications

When a shift is unfilled X days before:
- 3 days out: message the WhatsApp group with open slots
- 1 day out: coordinator gets urgent alert

---

## Phase 5: Escalation Logic

### p5-t1: Seniority-based escalation chain

depends-on: p4-t3
priority: 30
phase: phase-5
tags: backend, notifications

Add `seniority` field to volunteers table.
When a shift is unfilled and approaching:
- Notify available volunteers in ascending seniority order
- Wait for response before escalating to next person
- Coordinator notified if chain exhausted with no taker

---

## Verification

Each phase should be verified before moving to the next:

- **Phase 1**: `pytest tests/` — all signup rule tests pass. Manual curl to API endpoints.
- **Phase 2**: Send WhatsApp message to bot number, receive correct response. Send via `/send` endpoint.
- **Phase 3**: Sign up for a shift, verify notification rows created. Fast-forward time in test to verify send.
- **Phase 4**: As coordinator phone, run `status` and `gaps` commands. Verify correct output.
- **Phase 5**: Leave a shift unfilled, verify escalation messages sent in correct order.
