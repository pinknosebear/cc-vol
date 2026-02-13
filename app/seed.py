"""Seed helpers: monthly shifts, dummy volunteer profiles, and crafted signups."""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta

from app.models.shift import ShiftCreate, Shift, create_shift, get_robe_capacity, get_shifts_by_month
from app.models.signup import SignupCreate, Signup, create_signup, drop_signup, get_signups_by_volunteer
from app.models.volunteer import Volunteer, VolunteerCreate, create_volunteer, get_volunteer_by_phone
from app.rules.validator import validate_signup


def seed_month(db: sqlite3.Connection, year: int, month: int) -> int:
    """Create Kakad + Robe shifts for every day in the given month.

    Idempotent: skips any (date, shift_type) pair that already exists.
    Returns the number of shifts created.
    """
    num_days = calendar.monthrange(year, month)[1]
    created = 0

    for day in range(1, num_days + 1):
        d = date(year, month, day)
        d_iso = d.isoformat()

        for shift_type, capacity in [
            ("kakad", 1),
            ("robe", get_robe_capacity(d.weekday())),
        ]:
            existing = db.execute(
                "SELECT 1 FROM shifts WHERE date = ? AND shift_type = ?",
                (d_iso, shift_type),
            ).fetchone()
            if existing:
                continue

            create_shift(db, ShiftCreate(date=d, type=shift_type, capacity=capacity))
            created += 1

    return created


# ---------------------------------------------------------------------------
# Volunteer seed data
# ---------------------------------------------------------------------------

VOLUNTEER_DATA = [
    {"phone": "1111111111", "name": "Sonia", "is_coordinator": True},
    {"phone": "2222222222", "name": "Raghu", "is_coordinator": True},
    {"phone": "3333333333", "name": "Ganesh", "is_coordinator": False},
    {"phone": "4444444444", "name": "Anita", "is_coordinator": False},
    {"phone": "5555555555", "name": "Bhawna", "is_coordinator": False},
    {"phone": "6666666666", "name": "Seema", "is_coordinator": False},
    {"phone": "7777777777", "name": "Mili", "is_coordinator": False},
    {"phone": "8888888888", "name": "Kusum", "is_coordinator": False},
    {"phone": "9999999999", "name": "Lina", "is_coordinator": False},
    {"phone": "1010101010", "name": "Pravy", "is_coordinator": False},
]


def seed_volunteers(db: sqlite3.Connection) -> list[Volunteer]:
    """Create 10 deterministic dummy volunteers.

    Idempotent: skips any volunteer whose phone already exists.
    Returns the full list of volunteers (created or pre-existing).
    """
    result: list[Volunteer] = []
    for entry in VOLUNTEER_DATA:
        existing = get_volunteer_by_phone(db, entry["phone"])
        if existing is not None:
            result.append(existing)
            continue
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone=entry["phone"],
                name=entry["name"],
                is_coordinator=entry["is_coordinator"],
            ),
        )
        result.append(vol)
    return result


# ---------------------------------------------------------------------------
# Signup seed data
# ---------------------------------------------------------------------------

def _find_shift(shifts: list[Shift], target_date: date, shift_type: str) -> Shift:
    """Find a shift by date and type from the preloaded list."""
    for s in shifts:
        if s.date == target_date and s.type == shift_type:
            return s
    raise ValueError(f"No {shift_type} shift found for {target_date}")


def _do_signup(
    db: sqlite3.Connection,
    volunteer_id: int,
    shift: Shift,
    simulated_today: date,
) -> Signup | None:
    """Validate and create a signup, setting signed_up_at to simulated_today.

    Returns the Signup if created, None if validation failed.
    """
    violations = validate_signup(db, volunteer_id, shift.id, today=simulated_today)
    if violations:
        return None
    signup = create_signup(db, SignupCreate(volunteer_id=volunteer_id, shift_id=shift.id))
    # Override signed_up_at to match the simulated date so phase counting works
    db.execute(
        "UPDATE signups SET signed_up_at = ? WHERE id = ?",
        (simulated_today.isoformat(), signup.id),
    )
    db.commit()
    # Re-read to get updated signed_up_at
    row = db.execute("SELECT * FROM signups WHERE id = ?", (signup.id,)).fetchone()
    return Signup(
        id=row["id"],
        volunteer_id=row["volunteer_id"],
        shift_id=row["shift_id"],
        signed_up_at=row["signed_up_at"],
        dropped_at=row["dropped_at"],
    )


def seed_signups(db: sqlite3.Connection, year: int, month: int) -> dict[str, list[int]]:
    """Create crafted signup scenarios for the given month.

    Calls seed_month and seed_volunteers first to ensure data exists.
    Uses validate_signup before each signup to verify rules pass.

    Idempotent: returns existing signup IDs if signups already exist.

    Returns a dict mapping volunteer name to list of active signup IDs.
    """
    # Ensure shifts and volunteers exist
    seed_month(db, year, month)
    volunteers = seed_volunteers(db)

    # Build a lookup by phone
    vol_by_phone: dict[str, Volunteer] = {v.phone: v for v in volunteers}

    # Check idempotency: if any signups already exist for this month, return them
    month_str = f"{year:04d}-{month:02d}"
    existing_signups = False
    result: dict[str, list[int]] = {}
    for v in volunteers:
        sups = get_signups_by_volunteer(db, v.id, month_str)
        active = [s for s in sups if s.dropped_at is None]
        if active:
            existing_signups = True
        result[v.name] = [s.id for s in active]
    if existing_signups:
        return result

    # Load all shifts for the month
    all_shifts = get_shifts_by_month(db, year, month)

    month_start = date(year, month, 1)
    phase1_today = month_start - timedelta(days=15)
    phase2_today = month_start - timedelta(days=7)

    # Helper to get a shift
    def shift(day: int, stype: str) -> Shift:
        return _find_shift(all_shifts, date(year, month, day), stype)

    result = {}

    # --- Volunteer A: Sonia (1111111111) — 2 Kakad + 4 Robe = 6 (Phase 1 max) ---
    sonia = vol_by_phone["1111111111"]
    sonia_ids: list[int] = []
    # 2 Kakad shifts (days 3, 4)
    for day in [3, 4]:
        s = _do_signup(db, sonia.id, shift(day, "kakad"), phase1_today)
        if s:
            sonia_ids.append(s.id)
    # 4 Robe shifts (days 5, 6, 7, 8)
    for day in [5, 6, 7, 8]:
        s = _do_signup(db, sonia.id, shift(day, "robe"), phase1_today)
        if s:
            sonia_ids.append(s.id)
    result["Sonia"] = sonia_ids

    # --- Volunteer B: Raghu (2222222222) — 1 Thursday shift ---
    raghu = vol_by_phone["2222222222"]
    raghu_ids: list[int] = []
    # Feb 5 is Thursday (weekday=3)
    s = _do_signup(db, raghu.id, shift(5, "kakad"), phase1_today)
    if s:
        raghu_ids.append(s.id)
    result["Raghu"] = raghu_ids

    # --- Volunteer C: Ganesh (3333333333) — 6 Phase 1 + 2 Phase 2 = 8 ---
    ganesh = vol_by_phone["3333333333"]
    ganesh_ids: list[int] = []
    # Phase 1: 2 kakad + 4 robe = 6
    for day in [9, 10]:
        s = _do_signup(db, ganesh.id, shift(day, "kakad"), phase1_today)
        if s:
            ganesh_ids.append(s.id)
    for day in [11, 12, 13, 14]:
        s = _do_signup(db, ganesh.id, shift(day, "robe"), phase1_today)
        if s:
            ganesh_ids.append(s.id)
    # Phase 2: 2 additional robe shifts
    for day in [15, 16]:
        s = _do_signup(db, ganesh.id, shift(day, "robe"), phase2_today)
        if s:
            ganesh_ids.append(s.id)
    result["Ganesh"] = ganesh_ids

    # --- Volunteer D: Anita (4444444444) — 2 shifts, drop 1 ---
    anita = vol_by_phone["4444444444"]
    anita_ids: list[int] = []
    s1 = _do_signup(db, anita.id, shift(17, "robe"), phase1_today)
    s2 = _do_signup(db, anita.id, shift(18, "robe"), phase1_today)
    if s1:
        anita_ids.append(s1.id)
    if s2:
        # Drop second signup
        drop_signup(db, s2.id)
        # Don't add to active list
    result["Anita"] = anita_ids

    # --- Volunteer E: Bhawna (5555555555) — 1 shift only ---
    bhawna = vol_by_phone["5555555555"]
    bhawna_ids: list[int] = []
    s = _do_signup(db, bhawna.id, shift(19, "robe"), phase1_today)
    if s:
        bhawna_ids.append(s.id)
    result["Bhawna"] = bhawna_ids

    # --- Fill all slots for first couple days (days 1-2) ---
    # Use remaining volunteers: Seema, Mili, Kusum, Lina, Pravy
    fillers = [
        vol_by_phone["6666666666"],  # Seema
        vol_by_phone["7777777777"],  # Mili
        vol_by_phone["8888888888"],  # Kusum
        vol_by_phone["9999999999"],  # Lina
        vol_by_phone["1010101010"],  # Pravy
    ]
    for name in ["Seema", "Mili", "Kusum", "Lina", "Pravy"]:
        result.setdefault(name, [])

    filler_idx = 0
    for day in [1, 2]:
        for stype in ["kakad", "robe"]:
            sh = shift(day, stype)
            # Fill to capacity
            for _slot in range(sh.capacity):
                vol = fillers[filler_idx % len(fillers)]
                s = _do_signup(db, vol.id, sh, phase1_today)
                if s:
                    result[vol.name].append(s.id)
                filler_idx += 1

    # Days 25-28 are left completely empty (no signups needed)

    return result
