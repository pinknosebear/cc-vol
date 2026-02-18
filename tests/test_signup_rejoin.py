"""Tests for re-signup after drop."""

from app.db import create_tables, get_db_connection
from app.models.signup import SignupCreate, create_signup, drop_signup


def test_create_signup_reactivates_dropped_row():
    db = get_db_connection(":memory:")
    create_tables(db)

    vol_id = db.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        ("+15551230000", "Test Vol"),
    ).lastrowid
    shift_id = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        ("2026-02-21", "kakad", 1),
    ).lastrowid
    db.commit()

    created = create_signup(db, SignupCreate(volunteer_id=vol_id, shift_id=shift_id))
    drop_signup(db, created.id)

    rejoined = create_signup(db, SignupCreate(volunteer_id=vol_id, shift_id=shift_id))
    assert rejoined.id == created.id
    assert rejoined.dropped_at is None
