from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class NotificationCreate(BaseModel):
    volunteer_id: int
    type: Literal["reminder", "escalation", "welcome", "alert"]
    message: str


class Notification(BaseModel):
    id: int
    volunteer_id: int
    type: str
    message: str
    sent_at: Optional[datetime]
    ack_at: Optional[datetime]
    error: Optional[str]


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def _row_to_notification(row: sqlite3.Row) -> Notification:
    return Notification(
        id=row["id"],
        volunteer_id=row["volunteer_id"],
        type=row["type"],
        message=row["message"],
        sent_at=row["sent_at"],
        ack_at=row["ack_at"],
        error=row["error"],
    )


def create_notification(db: sqlite3.Connection, data: NotificationCreate) -> Notification:
    """Insert a new notification and return the created record."""
    cursor = db.execute(
        """INSERT INTO notifications (volunteer_id, type, message)
           VALUES (?, ?, ?)""",
        (data.volunteer_id, data.type, data.message),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM notifications WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_notification(row)


def get_notification(db: sqlite3.Connection, notification_id: int) -> Optional[Notification]:
    """Look up a notification by ID. Returns None if not found."""
    row = db.execute(
        "SELECT * FROM notifications WHERE id = ?", (notification_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_notification(row)


def list_notifications_by_volunteer(
    db: sqlite3.Connection, volunteer_id: int
) -> list[Notification]:
    """Return all notifications for a specific volunteer."""
    rows = db.execute(
        "SELECT * FROM notifications WHERE volunteer_id = ? ORDER BY id DESC",
        (volunteer_id,),
    ).fetchall()
    return [_row_to_notification(r) for r in rows]


def mark_sent(
    db: sqlite3.Connection, notification_id: int
) -> Optional[Notification]:
    """Mark a notification as sent by setting sent_at to current timestamp."""
    db.execute(
        "UPDATE notifications SET sent_at = CURRENT_TIMESTAMP WHERE id = ?",
        (notification_id,),
    )
    db.commit()
    return get_notification(db, notification_id)


def mark_acknowledged(
    db: sqlite3.Connection, notification_id: int
) -> Optional[Notification]:
    """Mark a notification as acknowledged by setting ack_at to current timestamp."""
    db.execute(
        "UPDATE notifications SET ack_at = CURRENT_TIMESTAMP WHERE id = ?",
        (notification_id,),
    )
    db.commit()
    return get_notification(db, notification_id)


def mark_error(
    db: sqlite3.Connection, notification_id: int, error_msg: str
) -> Optional[Notification]:
    """Mark a notification with an error message."""
    db.execute(
        "UPDATE notifications SET error = ? WHERE id = ?",
        (error_msg, notification_id),
    )
    db.commit()
    return get_notification(db, notification_id)
