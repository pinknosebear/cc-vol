"""Shift routes: month list and day detail endpoints."""

from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.models.shift import get_shifts_by_date, get_shifts_by_month
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

@router.get("", response_model=None)
def list_shifts(request: Request, month: str = Query(..., description="YYYY-MM")):
    """Return shifts for a given month with signup counts."""
    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(status_code=400, detail="month must be YYYY-MM format")

    year_str, month_str = month.split("-")
    year = int(year_str)
    mo = int(month_str)

    if mo < 1 or mo > 12:
        raise HTTPException(status_code=400, detail="month must be 01-12")

    db = request.app.state.db
    shifts = get_shifts_by_month(db, year, mo)

    results = []
    for s in shifts:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM signups WHERE shift_id = ? AND dropped_at IS NULL",
            (s.id,),
        ).fetchone()
        signup_count = row["cnt"] if row else 0

        results.append(
            {
                "id": s.id,
                "date": s.date.isoformat(),
                "type": s.type,
                "capacity": s.capacity,
                "signup_count": signup_count,
            }
        )

    return results


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
