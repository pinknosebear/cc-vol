"""Coordinator routes: shift fill-status overview."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.models.shift import get_shifts_by_date
from app.models.signup import get_active_signups_by_shift

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])


class ShiftStatus(BaseModel):
    id: int
    date: date
    type: Literal["kakad", "robe"]
    capacity: int
    signup_count: int
    status: Literal["filled", "open"]


@router.get("/status", response_model=list[ShiftStatus])
def coordinator_status(
    request: Request,
    date: Optional[str] = Query(default=None, description="Date in YYYY-MM-DD format"),
):
    """Return shifts for a date with fill status."""
    if date is None:
        target_date = __import__("datetime").date.today()
    else:
        try:
            target_date = __import__("datetime").date.fromisoformat(date)
        except ValueError:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid date format: {date}. Expected YYYY-MM-DD."},
            )

    db = request.app.state.db
    shifts = get_shifts_by_date(db, target_date)

    result = []
    for shift in shifts:
        active_signups = get_active_signups_by_shift(db, shift.id)
        signup_count = len(active_signups)
        result.append(
            ShiftStatus(
                id=shift.id,
                date=shift.date,
                type=shift.type,
                capacity=shift.capacity,
                signup_count=signup_count,
                status="filled" if signup_count >= shift.capacity else "open",
            )
        )

    return result
