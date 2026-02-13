"""Shift routes: day detail endpoint."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.models.shift import get_shifts_by_date
from app.models.signup import get_active_signups_by_shift


router = APIRouter(prefix="/api/shifts", tags=["shifts"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class VolunteerBrief(BaseModel):
    id: int
    name: str
    phone: str


class ShiftDetail(BaseModel):
    id: int
    date: date
    type: str
    capacity: int
    volunteers: list[VolunteerBrief]


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def _get_db(request: Request):
    return request.app.state.db


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{date}", response_model=list[ShiftDetail])
def get_day_detail(date: date, db=Depends(_get_db)):
    """Return all shifts for a given date with signed-up volunteers."""
    shifts = get_shifts_by_date(db, date)
    result = []
    for shift in shifts:
        active = get_active_signups_by_shift(db, shift.id)
        volunteers = []
        for signup in active:
            row = db.execute(
                "SELECT id, name, phone FROM volunteers WHERE id = ?",
                (signup.volunteer_id,),
            ).fetchone()
            if row:
                volunteers.append(
                    VolunteerBrief(id=row["id"], name=row["name"], phone=row["phone"])
                )
        result.append(
            ShiftDetail(
                id=shift.id,
                date=shift.date,
                type=shift.type,
                capacity=shift.capacity,
                volunteers=volunteers,
            )
        )
    return result
