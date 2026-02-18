from __future__ import annotations

import os
from datetime import date, timedelta
import sqlite3
from typing import Iterable

from apscheduler.schedulers.base import BaseScheduler

from app.db import get_db_connection
from app.notifications.sender import send_message


def schedule_shift_reminders(scheduler: BaseScheduler) -> None:
    scheduler.add_job(
        run_shift_reminders,
        "cron",
        hour=9,
        minute=0,
        args=[7],
        id="shift-reminder-7d",
        replace_existing=True,
    )
    scheduler.add_job(
        run_shift_reminders,
        "cron",
        hour=9,
        minute=0,
        args=[1],
        id="shift-reminder-1d",
        replace_existing=True,
    )


def run_shift_reminders(days_ahead: int) -> None:
    db_path = os.getenv("DB_PATH", "cc-vol.db")
    db = get_db_connection(db_path)
    try:
        _send_reminders_for_date(db, date.today() + timedelta(days=days_ahead), days_ahead)
    finally:
        db.close()


def _send_reminders_for_date(db: sqlite3.Connection, shift_date: date, days_ahead: int) -> None:
    rows = _get_signups_for_date(db, shift_date.isoformat())
    for row in rows:
        shift_label = "Kakad" if row["shift_type"] == "kakad" else "Robe"
        if days_ahead == 1:
            message = f"Reminder: You are scheduled for {shift_label} shift tomorrow ({shift_date})."
        else:
            message = (
                f"Reminder: You are scheduled for {shift_label} shift on {shift_date} "
                f"({days_ahead} days from now)."
            )

        if _notification_exists(db, row["volunteer_id"], message):
            continue

        send_message(db, row["volunteer_id"], message, notification_type="reminder")


def _get_signups_for_date(db: sqlite3.Connection, shift_date: str) -> Iterable[sqlite3.Row]:
    return db.execute(
        """
        SELECT v.id AS volunteer_id, s.shift_type
        FROM signups su
        JOIN shifts s ON s.id = su.shift_id
        JOIN volunteers v ON v.id = su.volunteer_id
        WHERE su.dropped_at IS NULL AND s.date = ?
        """,
        (shift_date,),
    ).fetchall()


def _notification_exists(db: sqlite3.Connection, volunteer_id: int, message: str) -> bool:
    row = db.execute(
        """
        SELECT 1 FROM notifications
        WHERE volunteer_id = ? AND type = 'reminder' AND message = ?
        LIMIT 1
        """,
        (volunteer_id, message),
    ).fetchone()
    return row is not None
