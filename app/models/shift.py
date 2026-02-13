"""Shift domain model: Pydantic schemas, CRUD functions, and helpers."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ShiftCreate(BaseModel):
    date: date
    type: Literal["kakad", "robe"]
    capacity: int


class Shift(BaseModel):
    id: int
    date: date
    type: Literal["kakad", "robe"]
    capacity: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_robe_capacity(weekday: int) -> int:
    """Return robe-shift capacity for a given weekday.

    weekday uses Python's date.weekday() convention: 0=Mon ... 6=Sun.
    Returns 3 for Sun(6)/Mon(0)/Wed(2)/Fri(4), 4 for Tue(1)/Thu(3)/Sat(5).
    """
    if weekday in (0, 2, 4, 6):  # Mon, Wed, Fri, Sun
        return 3
    return 4  # Tue, Thu, Sat


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def _row_to_shift(row: sqlite3.Row) -> Shift:
    """Convert a sqlite3.Row into a Shift model."""
    return Shift(
        id=row["id"],
        date=date.fromisoformat(row["date"]),
        type=row["shift_type"],
        capacity=row["capacity"],
        created_at=row["created_at"],
    )


def create_shift(db: sqlite3.Connection, data: ShiftCreate) -> Shift:
    """Insert a new shift and return it."""
    cursor = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (data.date.isoformat(), data.type, data.capacity),
    )
    db.commit()
    row = db.execute("SELECT * FROM shifts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_shift(row)


def get_shifts_by_date(db: sqlite3.Connection, target_date: date) -> list[Shift]:
    """Return all shifts for a given date."""
    rows = db.execute(
        "SELECT * FROM shifts WHERE date = ? ORDER BY shift_type",
        (target_date.isoformat(),),
    ).fetchall()
    return [_row_to_shift(r) for r in rows]


def get_shifts_by_month(db: sqlite3.Connection, year: int, month: int) -> list[Shift]:
    """Return all shifts within the given year/month."""
    # Build the YYYY-MM prefix for a LIKE query
    prefix = f"{year:04d}-{month:02d}-%"
    rows = db.execute(
        "SELECT * FROM shifts WHERE date LIKE ? ORDER BY date, shift_type",
        (prefix,),
    ).fetchall()
    return [_row_to_shift(r) for r in rows]
