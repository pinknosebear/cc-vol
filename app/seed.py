"""Seed helpers: monthly shifts and dummy volunteer profiles."""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date

from app.models.shift import ShiftCreate, create_shift, get_robe_capacity
from app.models.volunteer import Volunteer, VolunteerCreate, create_volunteer, get_volunteer_by_phone


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
