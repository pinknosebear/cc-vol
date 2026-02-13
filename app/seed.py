"""Seed monthly shift data into the database."""

from __future__ import annotations

import calendar
import sqlite3
from datetime import date

from app.models.shift import ShiftCreate, create_shift, get_robe_capacity


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
