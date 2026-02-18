"""Volunteer-related API routes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from app.models.volunteer import get_volunteer_by_phone, create_volunteer, VolunteerCreate, list_volunteers, remove_volunteer
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

@router.post("", status_code=201)
def add_volunteer(body: VolunteerCreate, request: Request):
    """Register a new volunteer."""
    db = request.app.state.db
    existing = get_volunteer_by_phone(db, body.phone)
    if existing:
        raise HTTPException(status_code=409, detail="Phone already registered")
    vol = create_volunteer(db, body)
    return {"id": vol.id, "phone": vol.phone, "name": vol.name, "is_coordinator": vol.is_coordinator}


@router.get("")
def get_volunteers(request: Request, status: Optional[str] = Query(None)):
    """List all volunteers.

    By default returns only approved volunteers.
    Coordinators can use ?status= to filter by a specific status.
    """
    db = request.app.state.db
    # If no status parameter provided, default to showing only approved volunteers
    filter_status = status if status is not None else "approved"
    vols = list_volunteers(db, status=filter_status)
    return [{"id": v.id, "phone": v.phone, "name": v.name, "is_coordinator": v.is_coordinator, "status": v.status} for v in vols]


@router.delete("/{phone}", status_code=204)
def delete_volunteer(phone: str, request: Request):
    """Remove a registered volunteer (soft-delete)."""
    db = request.app.state.db
    vol = remove_volunteer(db, phone)
    if vol is None:
        raise HTTPException(status_code=404, detail="Volunteer not found")
    return Response(status_code=204)


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
