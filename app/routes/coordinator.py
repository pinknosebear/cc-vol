"""Coordinator routes for volunteer availability queries."""

from __future__ import annotations

import sqlite3
from datetime import date

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.rules.queries import get_total_count

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])

RUNNING_MAX = 8


class AvailableVolunteer(BaseModel):
    id: int
    name: str
    phone: str
    total_signups: int
    remaining_slots: int


@router.get("/volunteers/available", response_model=list[AvailableVolunteer])
def get_available_volunteers(
    request: Request,
    date_param: str = Query(..., alias="date"),
):
    """Return volunteers who could still sign up for the given month.

    A volunteer is available if their total signups for the month
    containing ``date`` is less than the running maximum (8).
    """
    try:
        target_date = date.fromisoformat(date_param)
    except (ValueError, TypeError):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.")

    db: sqlite3.Connection = request.app.state.db
    year = target_date.year
    month = target_date.month

    rows = db.execute("SELECT id, name, phone FROM volunteers").fetchall()

    available: list[AvailableVolunteer] = []
    for row in rows:
        total = get_total_count(db, row["id"], year, month)
        if total < RUNNING_MAX:
            available.append(
                AvailableVolunteer(
                    id=row["id"],
                    name=row["name"],
                    phone=row["phone"],
                    total_signups=total,
                    remaining_slots=RUNNING_MAX - total,
                )
            )

    return available
