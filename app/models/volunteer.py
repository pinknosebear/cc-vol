from __future__ import annotations

import os
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


def _digits_only(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def normalize_phone(phone: str) -> str:
    """Normalize phone inputs to a consistent outbound-friendly format.

    Rules:
    - Keep E.164-style values as '+' plus digits.
    - 10-digit local numbers get default country code (defaults to +1).
    - 7-digit local numbers can be expanded when DEFAULT_AREA_CODE is set.
    """
    raw = (phone or "").strip()
    if not raw:
        return raw

    digits = _digits_only(raw)
    if not digits:
        return raw

    if raw.startswith("+"):
        return f"+{digits}"

    default_country = _digits_only(os.getenv("DEFAULT_COUNTRY_CODE", "1")) or "1"
    default_area = _digits_only(os.getenv("DEFAULT_AREA_CODE", ""))

    if len(digits) == 7 and default_area:
        digits = f"{default_area}{digits}"

    if len(digits) == 10 and digits[0] in "23456789":
        return f"+{default_country}{digits}"

    if len(digits) == 11 and digits.startswith(default_country):
        return f"+{digits}"

    if len(digits) > 11:
        return f"+{digits}"

    return digits


def _phone_lookup_candidates(phone: str) -> list[str]:
    raw = (phone or "").strip()
    if not raw:
        return []

    digits = _digits_only(raw)
    normalized = normalize_phone(raw)
    default_country = _digits_only(os.getenv("DEFAULT_COUNTRY_CODE", "1")) or "1"
    default_area = _digits_only(os.getenv("DEFAULT_AREA_CODE", ""))

    candidates: list[str] = []

    def add(value: str) -> None:
        if value and value not in candidates:
            candidates.append(value)

    add(normalized)
    add(raw)
    add(digits)

    if digits:
        add(f"+{digits}")

    if len(digits) == 10 and digits[0] in "23456789":
        add(f"+{default_country}{digits}")

    if len(digits) == 11 and digits.startswith(default_country):
        add(digits[len(default_country):])
        add(f"+{digits}")

    if len(digits) == 7 and default_area:
        local_ten = f"{default_area}{digits}"
        add(local_ten)
        add(f"+{default_country}{local_ten}")

    return candidates


def create_volunteer(db: sqlite3.Connection, data: VolunteerCreate) -> Volunteer:
    """Insert a new volunteer and return the created record."""
    normalized_phone = normalize_phone(data.phone)
    cursor = db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator, status) VALUES (?, ?, ?, ?)",
        (normalized_phone, data.name, data.is_coordinator, data.status),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM volunteers WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_volunteer(row)


def get_volunteer_by_phone(db: sqlite3.Connection, phone: str) -> Optional[Volunteer]:
    """Look up an active (non-removed) volunteer by phone number. Returns None if not found or removed."""
    candidates = _phone_lookup_candidates(phone)
    if not candidates:
        return None

    placeholders = ", ".join("?" for _ in candidates)
    rows = db.execute(
        f"SELECT * FROM volunteers WHERE removed_at IS NULL AND phone IN ({placeholders})",
        tuple(candidates),
    ).fetchall()
    if not rows:
        return None

    score = {value: idx for idx, value in enumerate(candidates)}
    best_row = min(rows, key=lambda row: score.get(row["phone"], len(candidates)))
    return _row_to_volunteer(best_row)


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
        ("approved", approver_id, vol.phone),
    )
    db.commit()

    # Fetch and return updated volunteer
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (vol.phone,)
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
        ("rejected", vol.phone),
    )
    db.commit()

    # Fetch and return updated volunteer
    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (vol.phone,)
    ).fetchone()
    return _row_to_volunteer(row)


def remove_volunteer(db: sqlite3.Connection, phone: str) -> Optional[Volunteer]:
    """Remove a volunteer by phone (soft-delete by setting removed_at).

    Returns the updated volunteer, or None if not found or already removed.
    """
    vol = get_volunteer_by_phone(db, phone)
    if vol is None:
        return None

    db.execute(
        "UPDATE volunteers SET removed_at = CURRENT_TIMESTAMP WHERE phone = ?",
        (vol.phone,),
    )
    db.commit()

    row = db.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (vol.phone,)
    ).fetchone()
    return _row_to_volunteer(row)
