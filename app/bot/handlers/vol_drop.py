"""Handler for volunteer drop command."""

from __future__ import annotations

import sqlite3
from datetime import date

from app.bot.auth import VolunteerContext
from app.models.signup import drop_signup


def handle_drop(
    db: sqlite3.Connection, context: VolunteerContext, args: dict
) -> str:
    """Process a volunteer's request to drop a shift.

    Args:
        db: SQLite connection.
        context: Authenticated volunteer context.
        args: Dict with "date" (datetime.date) and "type" (str, "kakad" or "robe").

    Returns:
        A user-facing message string.
    """
    shift_date: date = args["date"]
    shift_type: str = args["type"]

    # 1. Find the shift
    row = db.execute(
        "SELECT id FROM shifts WHERE date = ? AND shift_type = ?",
        (shift_date.isoformat(), shift_type),
    ).fetchone()
    if row is None:
        return f"No {shift_type} shift found on {shift_date}"

    shift_id = row["id"]

    # 2. Find active signup
    signup_row = db.execute(
        "SELECT id FROM signups WHERE volunteer_id = ? AND shift_id = ? AND dropped_at IS NULL",
        (context.volunteer_id, shift_id),
    ).fetchone()
    if signup_row is None:
        return f"You don't have an active signup for {shift_type} on {shift_date}"

    # 3. Drop the signup
    drop_signup(db, signup_row["id"])
    return f"Dropped {shift_type} shift on {shift_date}"
