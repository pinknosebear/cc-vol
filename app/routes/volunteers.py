"""Volunteer-related API routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.models.volunteer import get_volunteer_by_phone
from app.models.signup import get_signups_by_volunteer
from app.models.shift import Shift

router = APIRouter(prefix="/api/volunteers", tags=["volunteers"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ShiftDetail(BaseModel):
    shift_id: int
    date: date
    type: str
    capacity: int
    signup_id: int
    signed_up_at: datetime


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{phone}/shifts", response_model=list[ShiftDetail])
def get_volunteer_shifts(
    phone: str,
    request: Request,
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
):
    """Return active shifts for a volunteer in a given month."""
    db = request.app.state.db

    volunteer = get_volunteer_by_phone(db, phone)
    if volunteer is None:
        raise HTTPException(status_code=404, detail="Volunteer not found")

    signups = get_signups_by_volunteer(db, volunteer.id, month)
    active = [s for s in signups if s.dropped_at is None]

    results: list[ShiftDetail] = []
    for signup in active:
        row = db.execute(
            "SELECT * FROM shifts WHERE id = ?", (signup.shift_id,)
        ).fetchone()
        if row is None:
            continue
        shift = Shift(
            id=row["id"],
            date=date.fromisoformat(row["date"]),
            type=row["shift_type"],
            capacity=row["capacity"],
            created_at=row["created_at"],
        )
        results.append(
            ShiftDetail(
                shift_id=shift.id,
                date=shift.date,
                type=shift.type,
                capacity=shift.capacity,
                signup_id=signup.id,
                signed_up_at=signup.signed_up_at,
            )
        )

    return results
