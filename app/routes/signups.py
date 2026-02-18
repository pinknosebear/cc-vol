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


@router.post("", status_code=201)
def post_signup(body: SignupRequest, db: sqlite3.Connection = Depends(_get_db)):
    # Look up volunteer by phone
    volunteer = get_volunteer_by_phone(db, body.volunteer_phone)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    # Look up shift by id
    row = db.execute("SELECT id FROM shifts WHERE id = ?", (body.shift_id,)).fetchone()
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
    return signup.model_dump()


@router.delete("/{signup_id}", status_code=204)
def delete_signup(signup_id: int, db: sqlite3.Connection = Depends(_get_db)):
    """Drop a signup (soft-delete by setting dropped_at)."""
    row = db.execute(
        "SELECT * FROM signups WHERE id = ? AND dropped_at IS NULL", (signup_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Signup not found")

    drop_signup(db, signup_id)
    return Response(status_code=204)


class NotifyDropRequest(BaseModel):
    volunteer_phone: str
    shift_date: str
    shift_type: str


@router.post("/notify-drop", status_code=200)
def notify_coordinator_drop(body: NotifyDropRequest, db: sqlite3.Connection = Depends(_get_db)):
    """Notify a coordinator via WhatsApp that a volunteer dropped a shift within a week."""
    # Only notify if the shift is within 7 days
    try:
      shift_day = date.fromisoformat(body.shift_date)
    except ValueError:
      raise HTTPException(status_code=422, detail="Invalid shift_date format. Use YYYY-MM-DD.")

    if (shift_day - date.today()).days > 7:
      return {"success": False, "message": "Drop is more than 7 days away; no notification sent."}

    # Look up volunteer
    volunteer = get_volunteer_by_phone(db, body.volunteer_phone)
    if volunteer is None:
      raise HTTPException(status_code=404, detail="Volunteer not found")

    # Find a coordinator
    row = db.execute(
        "SELECT id FROM volunteers WHERE is_coordinator = 1 LIMIT 1"
    ).fetchone()
    if row is None:
        # No coordinator, just return success (notification not sent but not an error)
        return {"success": False, "message": "No coordinator found"}

    coordinator_id = row["id"]

    # Send message
    shift_label = "Kakad" if body.shift_type == "kakad" else "Robe"
    message = f"{volunteer.name} ({body.volunteer_phone}) dropped {shift_label} shift on {body.shift_date}"

    result = send_message(db, coordinator_id, message, notification_type="drop_alert")
    return result
