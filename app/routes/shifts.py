"""GET /api/shifts — return shifts for a given month with signup counts."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request, Query

from app.models.shift import get_shifts_by_month

router = APIRouter(prefix="/api")


@router.get("/shifts")
def list_shifts(request: Request, month: str = Query(..., description="YYYY-MM")):
    # Validate format
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
        # Count active (non-dropped) signups
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
