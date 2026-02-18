# cc-vol -- Volunteer Scheduling System

Scheduling system for daily volunteer shifts at a Sai Baba Temple. Replaces
WhatsApp group chat + Google Sheet signup process with a rules-driven system
that automates coordinator workflows.

## The Problem

~50 volunteers, 2-3 coordinators. Every day needs a Kakad shift and Robe shifts
filled. Currently managed through a WhatsApp group (noisy) and a Google Sheet
(manual). Coordinators spend time chasing people for empty slots.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite3 (included with Python on most systems)

### Backend (Python / FastAPI)

```bash
pip install -r requirements.txt
python -m app.seed          # generate shifts and test volunteers
uvicorn app.main:app --reload --port 8000
```

The API server and web UI run at `http://localhost:8000`.

- **Coordinator dashboard**: `http://localhost:8000/dashboard`
- **Volunteer portal**: `http://localhost:8000/volunteer`

### WhatsApp Bridge (Node.js)

```bash
cd wa-bridge/
npm install
npm start
```

On first launch the bridge prints a QR code to the terminal. Scan it with
WhatsApp on the coordinator's phone to link the session. The bridge connects
to the Python backend at `http://localhost:8000` by default.

## How It Works

The system runs as two separate processes that communicate over HTTP.

**Python backend (FastAPI)** -- owns all business logic, signup rules, shift
data, and coordinator tools. Every decision about whether a signup is valid,
what gaps exist, or who to remind goes through this process. SQLite is the
only datastore; no external database server is needed. Also serves the web
dashboard and volunteer portal as static HTML.

**Node.js bridge (wa-bridge)** -- a thin relay between WhatsApp and the Python
backend. It uses Baileys (unofficial WhatsApp Web client) to receive messages,
forwards them to `POST /wa/incoming` on the Python server, and sends the
response text back to the user on WhatsApp. The bridge contains no business
logic and no direct database access.

```
Volunteer sends WhatsApp message
        |
        v
  wa-bridge (Node.js)
        |  POST /wa/incoming {phone, message}
        v
  FastAPI (Python)
        |  parses command, validates rules, queries DB
        v
  wa-bridge receives response text
        |
        v
Volunteer receives WhatsApp reply
```

## Architecture

```
+--------------+     HTTP      +--------------+
|  WhatsApp    |<------------>|   FastAPI     |
|  (Baileys)   |  POST /send   |   (Python)   |
|  Node.js     |  POST /wa/in  |              |
+--------------+               |  SQLite DB   |
                               +--------------+
                                      |
                               +--------------+
                               |  Web UI      |
                               |  (Tailwind)  |
                               +--------------+
```

Two-process design. All business logic in Python. Thin WhatsApp relay in Node.js.
Uses Baileys (unofficial WhatsApp Web client via QR scan), not the Business API.

## Shift Structure

Each day has a Kakad shift and Robe shifts. Capacity varies by day of week.

| Day of week         | Kakad slots | Robe slots | Total per day |
|---------------------|-------------|------------|---------------|
| Sun, Mon, Wed, Fri  | 1           | 3          | 4             |
| Tue, Thu, Sat       | 1           | 4          | 5             |

**Monthly totals (~28 day month):**

| | Days | Slots/day | Subtotal |
|---|------|-----------|----------|
| Sun/Mon/Wed/Fri | 16 | 4 | 64 |
| Tue/Thu/Sat | 12 | 5 | 60 |
| **Total** | **28** | | **~124 slots/month** |

## Volunteer Registration & Approval

New volunteers register via WhatsApp bot. Their account starts as `pending`
until a coordinator approves it. This prevents unknown numbers from signing up.

```
Volunteer: register Priya Sharma
Bot: Thanks Priya! Your registration is pending coordinator approval.

Coordinator: pending
Bot: Pending registrations: [list]

Coordinator: approve +1234567890
Bot: Approved. Priya Sharma can now sign up for shifts.
```

Volunteer status lifecycle: `pending` → `approved` (or `rejected`).

## Signup Rules

Signups are spread across two phases before the month begins so that shifts
are distributed fairly across all volunteers. Phase 1 enforces strict per-type
caps (max Kakad, max Robe, max Thursday) to prevent any one person from
claiming too many popular slots. Phase 2 loosens the rules and lets volunteers
add a couple more shifts of any type. Once the month is underway, all limits
are removed entirely -- the priority shifts to making sure every slot is filled,
so anyone can pick up any open shift regardless of how many they already have.

### Phase 1 -- Two weeks before the month

| Rule | Limit |
|------|-------|
| Max Kakad shifts per volunteer | 2 |
| Max Robe shifts per volunteer | 4 |
| Max Thursday shifts per volunteer | 1 |
| **Max total from Phase 1** | **6** (2K + 4R) |

Kakad and Robe caps are independent. A volunteer can sign up for both Kakad
and Robe on the same day.

### Phase 2 -- One week before the month

| Rule | Limit |
|------|-------|
| Additional slots (any type) | +2 |
| Thursday restriction | None |
| Type restriction | None |
| **Running total max** | **8** (6 + 2) |

Phase 2 slots are unrestricted -- can be Kakad or Robe, can be Thursday,
no per-type caps.

### Mid-month pickup -- After the month starts

| Rule | Limit |
|------|-------|
| All limits | **None** |

If a shift is unfilled or someone drops, any volunteer can pick it up
regardless of how many shifts they already have.

### Summary

| Phase | Window | Kakad cap | Robe cap | Thu cap | Extra | Running max |
|-------|--------|-----------|----------|---------|-------|-------------|
| Phase 1 | 2 weeks before | 2 | 4 | 1 | -- | 6 |
| Phase 2 | 1 week before | -- | -- | -- | +2 any | 8 |
| Mid-month | After month starts | -- | -- | -- | unlimited | No cap |

## Notifications

The system sends WhatsApp notifications for time-sensitive events:

- **Late drop**: When a volunteer drops a shift within 24 hours of the shift
  time, the coordinator is notified so they can find a substitute quickly.

Notifications are queued in the database and sent via the wa-bridge. A
`notifications` table tracks sent/pending state to prevent duplicates.

## User Roles

| Role | Count | Capabilities |
|------|-------|-------------|
| Volunteer | ~50 | Register, sign up for shifts, drop shifts, view own schedule |
| Coordinator | 2-3 | All volunteer actions + approve/reject registrations, view gaps, find substitutes, see who's available |

Identity is phone number (via WhatsApp). No passwords, no accounts.

## Bot Commands

### Volunteer commands

| Command | Description |
|---------|-------------|
| `register <name>` | Register as a new volunteer (starts pending) |
| `signup <date> <type>` | Sign up for a shift |
| `drop <date> <type>` | Drop a shift |
| `my shifts` | List your upcoming shifts |
| `shifts <date>` | Show available shifts for a date |
| `help` | List commands |

### Coordinator commands

| Command | Description |
|---------|-------------|
| `pending` | List volunteers awaiting approval |
| `approve <phone>` | Approve a volunteer registration |
| `reject <phone>` | Reject a volunteer registration |
| `status <date>` | Who's signed up, what's empty |
| `gaps` | All unfilled upcoming shifts |
| `find sub <date> <type>` | List available volunteers for a shift |

## Web UI

The Python backend serves a web interface at `/dashboard` and `/volunteer`.

**Coordinator dashboard** (`/dashboard`): Month-at-a-glance grid showing
fill status for every shift. Click a day to see who's signed up and what's
empty. Month navigation, volunteer list, and gaps list are shown in side
panels.

**Volunteer portal** (`/volunteer`): Volunteers can view the shift calendar
and sign up or drop shifts without using WhatsApp.

## API Endpoints

### Shifts & Signups

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/shifts?month=YYYY-MM` | List shifts for month with signup counts |
| GET | `/api/shifts/{date}` | Shifts for a day with who's signed up |
| POST | `/api/signups` | Sign up (validates rules) |
| DELETE | `/api/signups/{id}` | Drop a shift |
| GET | `/api/volunteers/{phone}/shifts` | My upcoming shifts |

### Coordinator

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/coordinator/status?date=YYYY-MM-DD` | Shifts with fill status |
| GET | `/api/coordinator/gaps?month=YYYY-MM` | All unfilled shifts |
| GET | `/api/coordinator/volunteers/available?date=YYYY-MM-DD` | Who hasn't hit limits |

### WhatsApp

| Method | Path | Description |
|--------|------|-------------|
| POST | `/wa/incoming` | Receive message from wa-bridge, returns reply text |

## Data Model

```sql
volunteers    (id, phone, name, is_coordinator, status, created_at)
shifts        (id, date, type, capacity, created_at)
signups       (id, volunteer_id, shift_id, signed_up_at, dropped_at)
notifications (id, volunteer_id, message, sent_at, created_at)
```

- `volunteers.status`: 'pending', 'approved', or 'rejected'
- `shifts.type`: 'kakad' or 'robe'
- `shifts.capacity`: 1 for Kakad, 3 or 4 for Robe (varies by day of week)
- `signups.dropped_at`: NULL = active, timestamp = soft-deleted
- `UNIQUE(volunteer_id, shift_id)`: one signup per volunteer per shift
- `UNIQUE(date, type)`: one shift row per type per day

## Tech Stack

- **Backend**: Python, FastAPI, SQLite
- **Web UI**: HTML, Tailwind CSS, vanilla JS
- **WhatsApp bridge**: Node.js, @whiskeysockets/baileys
- **Testing**: pytest
- **Deployment**: Railway

## Development

**Run tests:**

```bash
pytest tests/ -v
```

**Seed test data:**

`app/seed.py` generates shifts for a given month and optionally creates test
volunteers and signups. Run it with `python -m app.seed` from the project root.

**Database:**

SQLite stores everything in a single file (`cc-vol.db`). No database server
to install or manage. The schema is created automatically on first run via
`app/db.py`.

## Project Structure

```
cc-vol/
├── app/
│   ├── main.py              # FastAPI app + HTML routes
│   ├── db.py                # SQLite connection + schema
│   ├── seed.py              # Shift + volunteer + signup seeding
│   ├── models/
│   │   ├── volunteer.py
│   │   ├── shift.py
│   │   ├── signup.py
│   │   └── notification.py
│   ├── rules/
│   │   ├── pure.py          # Pure validation functions (no DB)
│   │   ├── queries.py       # DB count queries
│   │   └── validator.py     # Orchestrator
│   ├── routes/
│   │   ├── shifts.py
│   │   ├── signups.py
│   │   ├── volunteers.py
│   │   ├── coordinator.py
│   │   └── wa_incoming.py
│   ├── bot/
│   │   ├── parser.py        # Message -> command
│   │   ├── auth.py          # Phone -> volunteer context
│   │   └── handlers/
│   │       ├── registration.py  # register / approve / reject / pending
│   │       ├── vol_signup.py
│   │       ├── vol_drop.py
│   │       ├── vol_query.py
│   │       └── coordinator.py
│   ├── notifications/
│   │   └── sender.py        # WhatsApp notification dispatch
│   └── static/
│       ├── dashboard.html   # Coordinator dashboard
│       ├── volunteer.html   # Volunteer portal
│       ├── chat.html        # Debug/test UI
│       ├── js/              # Dashboard + portal JS modules
│       └── css/             # Tailwind output
├── wa-bridge/               # Node.js WhatsApp service
├── tests/
├── plan.md
├── gantt.md
└── README.md
```
