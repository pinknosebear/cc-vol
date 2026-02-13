from __future__ import annotations

import sqlite3
from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class VolunteerCreate(BaseModel):
    phone: str
    name: str
    is_coordinator: bool = False


class Volunteer(BaseModel):
    id: int
    phone: str
    name: str
    is_coordinator: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def _row_to_volunteer(row: sqlite3.Row) -> Volunteer:
    return Volunteer(
        id=row["id"],
        phone=row["phone"],
        name=row["name"],
        is_coordinator=bool(row["is_coordinator"]),
        created_at=row["created_at"],
    )


def create_volunteer(db: sqlite3.Connection, data: VolunteerCreate) -> Volunteer:
    """Insert a new volunteer and return the created record."""
    cursor = db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator) VALUES (?, ?, ?)",
        (data.phone, data.name, data.is_coordinator),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM volunteers WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_volunteer(row)


def get_volunteer_by_phone(db: sqlite3.Connection, phone: str) -> Volunteer | None:
    """Look up a volunteer by phone number. Returns None if not found."""
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (phone,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_volunteer(row)


def list_volunteers(db: sqlite3.Connection) -> list[Volunteer]:
    """Return all volunteers."""
    rows = db.execute("SELECT * FROM volunteers").fetchall()
    return [_row_to_volunteer(r) for r in rows]
