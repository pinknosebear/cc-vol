from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class VolunteerCreate(BaseModel):
    phone: str
    name: str
    is_coordinator: bool = False
    status: str = "approved"


class Volunteer(BaseModel):
    id: int
    phone: str
    name: str
    is_coordinator: bool
    created_at: datetime
    status: str
    requested_at: Optional[datetime]
    approved_at: Optional[datetime]
    approved_by: Optional[int]
    removed_at: Optional[datetime]


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
        status=row["status"],
        requested_at=row["requested_at"],
        approved_at=row["approved_at"],
        approved_by=row["approved_by"],
        removed_at=row["removed_at"],
    )


def create_volunteer(db: sqlite3.Connection, data: VolunteerCreate) -> Volunteer:
    """Insert a new volunteer and return the created record."""
    cursor = db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator, status) VALUES (?, ?, ?, ?)",
        (data.phone, data.name, data.is_coordinator, data.status),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM volunteers WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_volunteer(row)


def get_volunteer_by_phone(db: sqlite3.Connection, phone: str) -> Optional[Volunteer]:
    """Look up an active (non-removed) volunteer by phone number. Returns None if not found or removed."""
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ? AND removed_at IS NULL", (phone,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_volunteer(row)


def list_volunteers(db: sqlite3.Connection, status: Optional[str] = None) -> list[Volunteer]:
    """Return all active (non-removed) volunteers, optionally filtered by status."""
    if status is None:
        rows = db.execute("SELECT * FROM volunteers WHERE removed_at IS NULL").fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM volunteers WHERE status = ? AND removed_at IS NULL", (status,)
        ).fetchall()
    return [_row_to_volunteer(r) for r in rows]


def get_pending_volunteers(db: sqlite3.Connection) -> list[Volunteer]:
    """Return all volunteers with status='pending'."""
    return list_volunteers(db, status="pending")


def approve_volunteer(
    db: sqlite3.Connection, phone: str, approver_id: int
) -> Optional[Volunteer]:
    """Approve a volunteer by phone. Returns the updated volunteer or None if not found."""
    # Check if volunteer exists
    vol = get_volunteer_by_phone(db, phone)
    if vol is None:
        return None

    # Update the volunteer
    db.execute(
        """UPDATE volunteers
           SET status = ?, approved_at = CURRENT_TIMESTAMP, approved_by = ?
           WHERE phone = ?""",
        ("approved", approver_id, phone),
    )
    db.commit()

    # Fetch and return updated volunteer
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (phone,)
    ).fetchone()
    return _row_to_volunteer(row)


def reject_volunteer(db: sqlite3.Connection, phone: str) -> Optional[Volunteer]:
    """Reject a volunteer by phone. Returns the updated volunteer or None if not found."""
    # Check if volunteer exists
    vol = get_volunteer_by_phone(db, phone)
    if vol is None:
        return None

    # Update the volunteer
    db.execute(
        """UPDATE volunteers SET status = ? WHERE phone = ?""",
        ("rejected", phone),
    )
    db.commit()

    # Fetch and return updated volunteer
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (phone,)
    ).fetchone()
    return _row_to_volunteer(row)


def remove_volunteer(db: sqlite3.Connection, phone: str) -> Optional[Volunteer]:
    """Remove a volunteer by phone (soft-delete by setting removed_at).

    Returns the updated volunteer, or None if not found or already removed.
    """
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ? AND removed_at IS NULL", (phone,)
    ).fetchone()
    if row is None:
        return None

    db.execute(
        "UPDATE volunteers SET removed_at = CURRENT_TIMESTAMP WHERE phone = ?",
        (phone,),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (phone,)
    ).fetchone()
    return _row_to_volunteer(row)
