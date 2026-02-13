"""Tests for the volunteer signup command handler."""

from datetime import date

from app.bot.auth import VolunteerContext
from app.bot.handlers.vol_signup import handle_signup
from app.models.signup import SignupCreate, create_signup
from app.models.volunteer import VolunteerCreate, create_volunteer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_volunteer(db, phone="1111", name="Alice", is_coordinator=False):
    vol = create_volunteer(db, VolunteerCreate(phone=phone, name=name, is_coordinator=is_coordinator))
    return VolunteerContext(volunteer_id=vol.id, phone=vol.phone, is_coordinator=vol.is_coordinator)


def _make_shift(db, shift_date="2026-03-15", shift_type="kakad", capacity=3):
    """Insert a shift directly and return its id."""
    cur = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (shift_date, shift_type, capacity),
    )
    db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_successful_signup(db):
    ctx = _make_volunteer(db)
    shift_id = _make_shift(db, shift_date="2026-03-15", shift_type="robe", capacity=3)

    # Use a today far enough before March to land in mid-month (no phase limits)
    result = handle_signup(db, ctx, {"date": date(2026, 3, 15), "type": "robe"})

    assert "Signed up for robe on 2026-03-15" == result

    # Verify the signup was persisted
    row = db.execute(
        "SELECT * FROM signups WHERE volunteer_id = ? AND shift_id = ?",
        (ctx.volunteer_id, shift_id),
    ).fetchone()
    assert row is not None


def test_no_matching_shift(db):
    ctx = _make_volunteer(db)

    result = handle_signup(db, ctx, {"date": date(2026, 3, 15), "type": "kakad"})

    assert result == "No kakad shift found on 2026-03-15"


def test_capacity_full_returns_violation(db):
    """When the shift is at capacity, the handler returns a violation message."""
    ctx1 = _make_volunteer(db, phone="1111", name="Alice")
    ctx2 = _make_volunteer(db, phone="2222", name="Bob")
    ctx3 = _make_volunteer(db, phone="3333", name="Carol")

    shift_id = _make_shift(db, shift_date="2026-03-15", shift_type="kakad", capacity=2)

    # Fill up the shift
    create_signup(db, SignupCreate(volunteer_id=ctx1.volunteer_id, shift_id=shift_id))
    create_signup(db, SignupCreate(volunteer_id=ctx2.volunteer_id, shift_id=shift_id))

    result = handle_signup(db, ctx3, {"date": date(2026, 3, 15), "type": "kakad"})

    assert "Cannot sign up:" in result
    assert "capacity" in result.lower() or "full" in result.lower()


def test_duplicate_signup_handled_gracefully(db):
    """Signing up for the same shift twice returns a friendly message."""
    ctx = _make_volunteer(db)
    _make_shift(db, shift_date="2026-03-15", shift_type="kakad", capacity=3)

    # First signup succeeds
    result1 = handle_signup(db, ctx, {"date": date(2026, 3, 15), "type": "kakad"})
    assert "Signed up" in result1

    # Second signup for same shift is a duplicate
    result2 = handle_signup(db, ctx, {"date": date(2026, 3, 15), "type": "kakad"})
    assert "Already signed up" in result2
