"""DB query functions for rule validation counts.

All queries exclude dropped signups (dropped_at IS NOT NULL).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def get_kakad_count(db: sqlite3.Connection, volunteer_id: int, year: int, month: int) -> int:
    """Count active kakad signups for volunteer in given month."""
    prefix = f"{year:04d}-{month:02d}-%"
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM signups s
        JOIN shifts sh ON s.shift_id = sh.id
        WHERE s.volunteer_id = ?
          AND s.dropped_at IS NULL
          AND sh.date LIKE ?
          AND sh.shift_type = 'kakad'
        """,
        (volunteer_id, prefix),
    ).fetchone()
    return row["cnt"]


def get_robe_count(db: sqlite3.Connection, volunteer_id: int, year: int, month: int) -> int:
    """Count active robe signups for volunteer in given month."""
    prefix = f"{year:04d}-{month:02d}-%"
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM signups s
        JOIN shifts sh ON s.shift_id = sh.id
        WHERE s.volunteer_id = ?
          AND s.dropped_at IS NULL
          AND sh.date LIKE ?
          AND sh.shift_type = 'robe'
        """,
        (volunteer_id, prefix),
    ).fetchone()
    return row["cnt"]


def get_total_count(db: sqlite3.Connection, volunteer_id: int, year: int, month: int) -> int:
    """Count all active signups for volunteer in given month."""
    prefix = f"{year:04d}-{month:02d}-%"
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM signups s
        JOIN shifts sh ON s.shift_id = sh.id
        WHERE s.volunteer_id = ?
          AND s.dropped_at IS NULL
          AND sh.date LIKE ?
        """,
        (volunteer_id, prefix),
    ).fetchone()
    return row["cnt"]


def get_thursday_count(db: sqlite3.Connection, volunteer_id: int, year: int, month: int) -> int:
    """Count active Thursday signups for volunteer in given month."""
    prefix = f"{year:04d}-{month:02d}-%"
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM signups s
        JOIN shifts sh ON s.shift_id = sh.id
        WHERE s.volunteer_id = ?
          AND s.dropped_at IS NULL
          AND sh.date LIKE ?
          AND strftime('%w', sh.date) = '4'
        """,
        (volunteer_id, prefix),
    ).fetchone()
    return row["cnt"]


def get_phase2_count(db: sqlite3.Connection, volunteer_id: int, year: int, month: int) -> int:
    """Count signups created during the Phase 2 window.

    Phase 2 window = 7-13 days before the first of the target month.
    That means signed_up_at falls in [month_start - 13 days, month_start - 7 days]
    (inclusive on both ends, comparing date portion only).
    """
    month_start = date(year, month, 1)
    phase2_start = (month_start - timedelta(days=13)).isoformat()
    phase2_end = (month_start - timedelta(days=7)).isoformat()
    prefix = f"{year:04d}-{month:02d}-%"
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM signups s
        JOIN shifts sh ON s.shift_id = sh.id
        WHERE s.volunteer_id = ?
          AND s.dropped_at IS NULL
          AND sh.date LIKE ?
          AND date(s.signed_up_at) >= ?
          AND date(s.signed_up_at) <= ?
        """,
        (volunteer_id, prefix, phase2_start, phase2_end),
    ).fetchone()
    return row["cnt"]


def get_shift_signup_count(db: sqlite3.Connection, shift_id: int) -> int:
    """Count active signups for a specific shift."""
    row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM signups
        WHERE shift_id = ?
          AND dropped_at IS NULL
        """,
        (shift_id,),
    ).fetchone()
    return row["cnt"]


def get_shift_capacity(db: sqlite3.Connection, shift_id: int) -> int:
    """Get capacity of a specific shift."""
    row = db.execute(
        "SELECT capacity FROM shifts WHERE id = ?",
        (shift_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Shift {shift_id} not found")
    return row["capacity"]
