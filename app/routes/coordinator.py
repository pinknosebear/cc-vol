"""Coordinator routes: shift status overview, gap analysis, volunteer availability."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.models.shift import get_shifts_by_date
from app.models.signup import get_active_signups_by_shift

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])


def _get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


# ---------------------------------------------------------------------------
# GET /status
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# GET /gaps
# ---------------------------------------------------------------------------

class ShiftGap(BaseModel):
    id: int
    date: str
    type: str
    capacity: int
    signup_count: int
    gap_size: int


@router.get("/gaps", response_model=list[ShiftGap])
def get_gaps(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: sqlite3.Connection = Depends(_get_db),
) -> list[ShiftGap]:
    """Return shifts where signup_count < capacity (unfilled shifts)."""
    rows = db.execute(
        """
        SELECT
            sh.id,
            sh.date,
            sh.shift_type AS type,
            sh.capacity,
            COUNT(s.id) AS signup_count
        FROM shifts sh
        LEFT JOIN signups s
            ON s.shift_id = sh.id AND s.dropped_at IS NULL
        WHERE sh.date LIKE ?
        GROUP BY sh.id
        HAVING signup_count < sh.capacity
        ORDER BY sh.date, sh.shift_type
        """,
        (f"{month}-%",),
    ).fetchall()

    return [
        ShiftGap(
            id=row["id"],
            date=row["date"],
            type=row["type"],
            capacity=row["capacity"],
            signup_count=row["signup_count"],
            gap_size=row["capacity"] - row["signup_count"],
        )
        for row in rows
    ]
