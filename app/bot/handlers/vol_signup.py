"""Volunteer signup command handler."""

from __future__ import annotations

import sqlite3
from datetime import date

from app.bot.auth import VolunteerContext
from app.models.signup import SignupCreate, create_signup
from app.rules.validator import validate_signup


def handle_signup(
    db: sqlite3.Connection,
    context: VolunteerContext,
    args: dict,
) -> str:
    """Process a volunteer signup request.

    Parameters
    ----------
    db:
        SQLite connection with Row factory.
    context:
        Authenticated volunteer context.
    args:
        Dict with keys ``date`` (datetime.date) and ``type`` (str: "kakad" or "robe").

    Returns
    -------
    str
        A user-facing message describing the outcome.
    """
    shift_date: date = args["date"]
    shift_type: str = args["type"]

    # 1. Look up the shift
    row = db.execute(
        "SELECT id FROM shifts WHERE date = ? AND shift_type = ?",
        (shift_date.isoformat(), shift_type),
    ).fetchone()

    if row is None:
        return f"No {shift_type} shift found on {shift_date}"

    shift_id: int = row["id"]

    # 2. Validate against rules
    violations = validate_signup(db, context.volunteer_id, shift_id)
    if violations:
        reasons = "\n".join(f"- {v.reason}" for v in violations)
        return f"Cannot sign up:\n{reasons}"

    # 3. Create the signup
    try:
        create_signup(db, SignupCreate(volunteer_id=context.volunteer_id, shift_id=shift_id))
    except sqlite3.IntegrityError:
        return f"Already signed up for {shift_type} on {shift_date}"

    return f"Signed up for {shift_type} on {shift_date}"
