"""Volunteer query command handlers."""

from __future__ import annotations

import sqlite3
from datetime import date

from app.bot.auth import VolunteerContext


def handle_my_shifts(
    db: sqlite3.Connection, context: VolunteerContext, args: dict
) -> str:
    """Return a formatted list of the volunteer's active shifts for a month.

    Args:
        db: SQLite connection.
        context: Authenticated volunteer context.
        args: dict with optional key "month" (str, "YYYY-MM").
              Defaults to current month if not specified.
    """
    month = args.get("month") or date.today().strftime("%Y-%m")

    rows = db.execute(
        """
        SELECT s.date, s.shift_type
        FROM signups su
        JOIN shifts s ON su.shift_id = s.id
        WHERE su.volunteer_id = ?
          AND su.dropped_at IS NULL
          AND s.date LIKE ?
        ORDER BY s.date, s.shift_type
        """,
        (context.volunteer_id, f"{month}%"),
    ).fetchall()

    if not rows:
        return f"You have no shifts for {month}"

    lines = [f"Your shifts for {month}:"]
    for row in rows:
        lines.append(f"- {row['date']} {row['shift_type']}")
    return "\n".join(lines)


def handle_shifts(
    db: sqlite3.Connection, context: VolunteerContext, args: dict
) -> str:
    """Return a formatted summary of all shifts on a given date.

    Args:
        db: SQLite connection.
        context: Authenticated volunteer context.
        args: dict with key "date" (datetime.date).
    """
    target_date: date = args["date"]
    date_str = target_date.isoformat()

    rows = db.execute(
        """
        SELECT s.id, s.shift_type, s.capacity,
               COUNT(su.id) AS signup_count
        FROM shifts s
        LEFT JOIN signups su
            ON su.shift_id = s.id AND su.dropped_at IS NULL
        WHERE s.date = ?
        GROUP BY s.id
        ORDER BY s.shift_type
        """,
        (date_str,),
    ).fetchall()

    if not rows:
        return f"No shifts found for {date_str}"

    lines = [f"Shifts for {date_str}:"]
    for row in rows:
        lines.append(
            f"- {row['shift_type']}: {row['signup_count']}/{row['capacity']}"
        )
    return "\n".join(lines)
