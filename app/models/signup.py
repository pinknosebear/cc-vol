"""Signup domain model: Pydantic schemas and CRUD functions."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SignupCreate(BaseModel):
    volunteer_id: int
    shift_id: int


class Signup(BaseModel):
    id: int
    volunteer_id: int
    shift_id: int
    signed_up_at: datetime
    dropped_at: Optional[datetime]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def _row_to_signup(row: sqlite3.Row) -> Signup:
    """Convert a sqlite3.Row into a Signup model."""
    return Signup(
        id=row["id"],
        volunteer_id=row["volunteer_id"],
        shift_id=row["shift_id"],
        signed_up_at=row["signed_up_at"],
        dropped_at=row["dropped_at"],
    )


def create_signup(db: sqlite3.Connection, data: SignupCreate) -> Signup:
    """Insert a new signup and return it."""
    existing = db.execute(
        "SELECT * FROM signups WHERE volunteer_id = ? AND shift_id = ?",
        (data.volunteer_id, data.shift_id),
    ).fetchone()
    if existing is not None:
        if existing["dropped_at"] is not None:
            db.execute(
                "UPDATE signups SET dropped_at = NULL, signed_up_at = CURRENT_TIMESTAMP WHERE id = ?",
                (existing["id"],),
            )
            db.commit()
            row = db.execute(
                "SELECT * FROM signups WHERE id = ?", (existing["id"],)
            ).fetchone()
            return _row_to_signup(row)
        return _row_to_signup(existing)

    cursor = db.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (data.volunteer_id, data.shift_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM signups WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_signup(row)


def drop_signup(db: sqlite3.Connection, signup_id: int) -> Optional[Signup]:
    """Set dropped_at on a signup. Returns updated signup or None if not found."""
    db.execute(
        "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE id = ?",
        (signup_id,),
    )
    db.commit()
    row = db.execute("SELECT * FROM signups WHERE id = ?", (signup_id,)).fetchone()
    if row is None:
        return None
    return _row_to_signup(row)


def get_signups_by_volunteer(
    db: sqlite3.Connection, volunteer_id: int, month: str
) -> list[Signup]:
    """Return all signups for a volunteer in a given month.

    month should be in 'YYYY-MM' format. Joins with shifts to filter by
    shift date.
    """
    rows = db.execute(
        """
        SELECT s.* FROM signups s
        JOIN shifts sh ON s.shift_id = sh.id
        WHERE s.volunteer_id = ? AND sh.date LIKE ?
        ORDER BY sh.date
        """,
        (volunteer_id, f"{month}-%"),
    ).fetchall()
    return [_row_to_signup(r) for r in rows]


def get_signups_by_shift(db: sqlite3.Connection, shift_id: int) -> list[Signup]:
    """Return all signups for a given shift (including dropped)."""
    rows = db.execute(
        "SELECT * FROM signups WHERE shift_id = ? ORDER BY signed_up_at",
        (shift_id,),
    ).fetchall()
    return [_row_to_signup(r) for r in rows]


def get_active_signups_by_shift(db: sqlite3.Connection, shift_id: int) -> list[Signup]:
    """Return only active (non-dropped) signups for a given shift."""
    rows = db.execute(
        "SELECT * FROM signups WHERE shift_id = ? AND dropped_at IS NULL ORDER BY signed_up_at",
        (shift_id,),
    ).fetchall()
    return [_row_to_signup(r) for r in rows]
