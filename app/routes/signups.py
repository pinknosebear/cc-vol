"""Signup route handlers."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.main import get_db
from app.models.signup import SignupCreate, Signup, create_signup
from app.models.volunteer import get_volunteer_by_phone
from app.rules.validator import validate_signup

router = APIRouter(prefix="/api/signups", tags=["signups"])


class SignupRequest(BaseModel):
    volunteer_phone: str
    shift_id: int


@router.post("", status_code=201)
def post_signup(body: SignupRequest, db: sqlite3.Connection = Depends(get_db)):
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
        "SELECT id FROM signups WHERE volunteer_id = ? AND shift_id = ?",
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
