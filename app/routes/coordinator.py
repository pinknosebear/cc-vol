"""Coordinator routes for shift gap analysis."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])


class ShiftGap(BaseModel):
    id: int
    date: str
    type: str
    capacity: int
    signup_count: int
    gap_size: int


def _get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


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
