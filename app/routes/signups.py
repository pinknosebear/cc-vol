"""Signup route handlers."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.models.signup import drop_signup

router = APIRouter(prefix="/api/signups", tags=["signups"])


def _get_db(request: Request) -> sqlite3.Connection:
    return request.app.state.db


@router.delete("/{signup_id}", status_code=204)
def delete_signup(signup_id: int, db: sqlite3.Connection = Depends(_get_db)):
    """Drop a signup (soft-delete by setting dropped_at)."""
    # Check if signup exists and is not already dropped
    row = db.execute(
        "SELECT * FROM signups WHERE id = ? AND dropped_at IS NULL", (signup_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Signup not found")

    drop_signup(db, signup_id)
    return Response(status_code=204)
