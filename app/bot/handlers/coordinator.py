"""Coordinator command handlers for the WhatsApp bot.

All handlers assume context.is_coordinator == True (caller checks this).
"""

from __future__ import annotations

import sqlite3
from datetime import date

from app.bot.auth import VolunteerContext
from app.rules.queries import get_total_count


def handle_status(db: sqlite3.Connection, context: VolunteerContext, args: dict) -> str:
    """Show shift status for a given date.

    args: {"date": datetime.date}
    """
    target_date: date = args["date"]
    date_str = target_date.isoformat()

    rows = db.execute(
        """
        SELECT sh.id, sh.shift_type, sh.capacity,
               COUNT(s.id) AS signup_count
        FROM shifts sh
        LEFT JOIN signups s ON s.shift_id = sh.id AND s.dropped_at IS NULL
        WHERE sh.date = ?
        GROUP BY sh.id
        ORDER BY sh.shift_type
        """,
        (date_str,),
    ).fetchall()

    if not rows:
        return f"No shifts found for {date_str}"

    lines = [f"*Status for {date_str}*"]
    for row in rows:
        shift_type = row["shift_type"]
        signup_count = row["signup_count"]
        capacity = row["capacity"]
        status = "filled" if signup_count >= capacity else "open"
        lines.append(f"- {shift_type}: {signup_count}/{capacity} ({status})")

    return "\n".join(lines)


def handle_gaps(db: sqlite3.Connection, context: VolunteerContext, args: dict) -> str:
    """Show unfilled shifts for a given month.

    args: {"month": str}  # "YYYY-MM"
    """
    month: str = args["month"]
    prefix = f"{month}-%"

    rows = db.execute(
        """
        SELECT sh.id, sh.date, sh.shift_type, sh.capacity,
               COUNT(s.id) AS signup_count
        FROM shifts sh
        LEFT JOIN signups s ON s.shift_id = sh.id AND s.dropped_at IS NULL
        WHERE sh.date LIKE ?
        GROUP BY sh.id
        HAVING COUNT(s.id) < sh.capacity
        ORDER BY sh.date, sh.shift_type
        """,
        (prefix,),
    ).fetchall()

    if not rows:
        return f"All shifts filled for {month}!"

    lines = [f"*Gaps for {month}*"]
    for row in rows:
        gap_size = row["capacity"] - row["signup_count"]
        lines.append(f"- {row['date']} {row['shift_type']}: {gap_size} needed")

    return "\n".join(lines)


def handle_find_sub(db: sqlite3.Connection, context: VolunteerContext, args: dict) -> str:
    """Find available volunteers who could fill a given shift.

    args: {"date": datetime.date, "type": str}
    """
    target_date: date = args["date"]
    shift_type: str = args["type"]
    date_str = target_date.isoformat()

    # Find the shift
    shift_row = db.execute(
        "SELECT id FROM shifts WHERE date = ? AND shift_type = ?",
        (date_str, shift_type),
    ).fetchone()

    if shift_row is None:
        return f"No {shift_type} shift found for {date_str}"

    shift_id = shift_row["id"]

    # Get all volunteers not already signed up for this shift
    volunteers = db.execute(
        """
        SELECT v.id, v.name, v.phone
        FROM volunteers v
        WHERE v.id NOT IN (
            SELECT s.volunteer_id FROM signups s
            WHERE s.shift_id = ? AND s.dropped_at IS NULL
        )
        ORDER BY v.name
        """,
        (shift_id,),
    ).fetchall()

    year = target_date.year
    month = target_date.month

    available = []
    for vol in volunteers:
        total = get_total_count(db, vol["id"], year, month)
        if total < 8:
            available.append((vol["name"], vol["phone"]))

    if not available:
        return "No available volunteers found"

    lines = [f"*Available subs for {date_str} {shift_type}*"]
    for name, phone in available:
        lines.append(f"- {name} ({phone})")

    return "\n".join(lines)
