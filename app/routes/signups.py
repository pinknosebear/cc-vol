"""Signup route handlers."""

from __future__ import annotations

import sqlite3

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.models.signup import SignupCreate, create_signup, drop_signup
from app.models.volunteer import get_volunteer_by_phone
from app.rules.validator import validate_signup
from app.notifications.sender import send_message

router = APIRouter(prefix="/api/signups", tags=["signups"])


def _get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


class SignupRequest(BaseModel):
    volunteer_phone: str
    shift_id: int


def _recent_drop_alert_exists(db: sqlite3.Connection, coordinator_id: int, message: str) -> bool:
    row = db.execute(
        """
        SELECT 1
        FROM notifications
        WHERE volunteer_id = ?
          AND type = 'alert'
          AND message = ?
          AND sent_at IS NOT NULL
          AND sent_at >= datetime('now', '-2 minutes')
        LIMIT 1
        """,
        (coordinator_id, message),
    ).fetchone()
    return row is not None


def _notify_coordinator_drop(
    db: sqlite3.Connection,
    volunteer_name: str,
    volunteer_phone: str,
    shift_date: str,
    shift_type: str,
) -> dict:
    """Notify coordinator for drops within 7 days. Never raises on "no-op" cases."""
    shift_day = date.fromisoformat(shift_date)
    if (shift_day - date.today()).days > 7:
        return {"success": False, "message": "Drop is more than 7 days away; no notification sent."}

    coordinator_row = db.execute(
        "SELECT id FROM volunteers WHERE is_coordinator = 1 AND removed_at IS NULL LIMIT 1"
    ).fetchone()
    if coordinator_row is None:
        return {"success": False, "message": "No coordinator found"}

    coordinator_id = coordinator_row["id"]
    shift_label = "Kakad" if shift_type == "kakad" else "Robe"
    message = f"{volunteer_name} ({volunteer_phone}) dropped {shift_label} shift on {shift_date}"

    if _recent_drop_alert_exists(db, coordinator_id, message):
        return {"success": True, "message": "Drop alert already sent recently"}

    return send_message(db, coordinator_id, message, notification_type="alert")


@router.post("", status_code=201)
def post_signup(body: SignupRequest, db: sqlite3.Connection = Depends(_get_db)):
    # Look up volunteer by phone
    volunteer = get_volunteer_by_phone(db, body.volunteer_phone)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    # Look up shift by id
    row = db.execute(
        "SELECT id, shift_type, date FROM shifts WHERE id = ?", (body.shift_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Check for duplicate signup
    existing = db.execute(
        "SELECT id FROM signups WHERE volunteer_id = ? AND shift_id = ? AND dropped_at IS NULL",
        (volunteer.id, body.shift_id),
    ).fetchone()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Duplicate signup")

    # Validate rules
    violations = validate_signup(db, volunteer.id, body.shift_id)
    if violations:
        raise HTTPException(
            status_code=422,
            detail=[{"reason": v.reason} for v in violations],
        )

    # Create signup
    signup = create_signup(db, SignupCreate(volunteer_id=volunteer.id, shift_id=body.shift_id))

    shift_label = "Kakad" if row["shift_type"] == "kakad" else "Robe"
    message = f"Signup confirmed: {shift_label} shift on {row['date']}."
    send_message(db, volunteer.id, message, notification_type="alert")

    return signup.model_dump()


@router.delete("/{signup_id}", status_code=204)
def delete_signup(signup_id: int, db: sqlite3.Connection = Depends(_get_db)):
    """Drop a signup (soft-delete by setting dropped_at)."""
    row = db.execute(
        """
        SELECT su.id, su.dropped_at, sh.date AS shift_date, sh.shift_type, v.name AS volunteer_name, v.phone AS volunteer_phone
        FROM signups su
        JOIN shifts sh ON sh.id = su.shift_id
        JOIN volunteers v ON v.id = su.volunteer_id
        WHERE su.id = ? AND su.dropped_at IS NULL
        """,
        (signup_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Signup not found")

    drop_signup(db, signup_id)
    try:
        _notify_coordinator_drop(
            db,
            volunteer_name=row["volunteer_name"],
            volunteer_phone=row["volunteer_phone"],
            shift_date=row["shift_date"],
            shift_type=row["shift_type"],
        )
    except Exception as exc:
        # Notification failure should not block dropping the shift.
        print(f"Drop notification failed for signup {signup_id}: {exc}")
    return Response(status_code=204)


class NotifyDropRequest(BaseModel):
    volunteer_phone: str
    shift_date: str
    shift_type: str


@router.post("/notify-drop", status_code=200)
def notify_coordinator_drop(body: NotifyDropRequest, db: sqlite3.Connection = Depends(_get_db)):
    """Notify a coordinator via WhatsApp that a volunteer dropped a shift within a week."""
    try:
        date.fromisoformat(body.shift_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid shift_date format. Use YYYY-MM-DD.")

    # Look up volunteer
    volunteer = get_volunteer_by_phone(db, body.volunteer_phone)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    return _notify_coordinator_drop(
        db,
        volunteer_name=volunteer.name,
        volunteer_phone=volunteer.phone,
        shift_date=body.shift_date,
        shift_type=body.shift_type,
    )
