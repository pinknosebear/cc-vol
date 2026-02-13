"""Tests for the signup domain model."""

import sqlite3
from datetime import date

import pytest

from app.models.volunteer import VolunteerCreate, create_volunteer
from app.models.shift import ShiftCreate, create_shift
from app.models.signup import (
    Signup,
    SignupCreate,
    create_signup,
    drop_signup,
    get_signups_by_volunteer,
    get_signups_by_shift,
    get_active_signups_by_shift,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_volunteer(db, phone="+1000000000", name="Test Vol"):
    return create_volunteer(db, VolunteerCreate(phone=phone, name=name))


def _make_shift(db, d=date(2025, 6, 15), shift_type="kakad", capacity=1):
    return create_shift(db, ShiftCreate(date=d, type=shift_type, capacity=capacity))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_signup(db: sqlite3.Connection):
    """Create a signup and verify all returned fields."""
    vol = _make_volunteer(db)
    shift = _make_shift(db)
    signup = create_signup(db, SignupCreate(volunteer_id=vol.id, shift_id=shift.id))

    assert isinstance(signup, Signup)
    assert signup.id is not None
    assert signup.volunteer_id == vol.id
    assert signup.shift_id == shift.id
    assert signup.signed_up_at is not None
    assert signup.dropped_at is None


def test_drop_signup(db: sqlite3.Connection):
    """drop_signup sets dropped_at timestamp."""
    vol = _make_volunteer(db)
    shift = _make_shift(db)
    signup = create_signup(db, SignupCreate(volunteer_id=vol.id, shift_id=shift.id))

    dropped = drop_signup(db, signup.id)
    assert dropped is not None
    assert dropped.dropped_at is not None
    assert dropped.id == signup.id


def test_get_signups_by_volunteer_month_filter(db: sqlite3.Connection):
    """get_signups_by_volunteer filters by month via shift date."""
    vol = _make_volunteer(db)
    shift_jun = _make_shift(db, d=date(2025, 6, 15))
    shift_jul = _make_shift(db, d=date(2025, 7, 1))

    create_signup(db, SignupCreate(volunteer_id=vol.id, shift_id=shift_jun.id))
    create_signup(db, SignupCreate(volunteer_id=vol.id, shift_id=shift_jul.id))

    jun_signups = get_signups_by_volunteer(db, vol.id, "2025-06")
    assert len(jun_signups) == 1
    assert jun_signups[0].shift_id == shift_jun.id

    jul_signups = get_signups_by_volunteer(db, vol.id, "2025-07")
    assert len(jul_signups) == 1
    assert jul_signups[0].shift_id == shift_jul.id


def test_get_signups_by_shift(db: sqlite3.Connection):
    """get_signups_by_shift returns all signups including dropped."""
    vol1 = _make_volunteer(db, phone="+1111")
    vol2 = _make_volunteer(db, phone="+2222")
    shift = _make_shift(db)

    s1 = create_signup(db, SignupCreate(volunteer_id=vol1.id, shift_id=shift.id))
    create_signup(db, SignupCreate(volunteer_id=vol2.id, shift_id=shift.id))
    drop_signup(db, s1.id)

    all_signups = get_signups_by_shift(db, shift.id)
    assert len(all_signups) == 2


def test_active_signups_excludes_dropped(db: sqlite3.Connection):
    """get_active_signups_by_shift excludes dropped signups."""
    vol1 = _make_volunteer(db, phone="+3333")
    vol2 = _make_volunteer(db, phone="+4444")
    shift = _make_shift(db)

    s1 = create_signup(db, SignupCreate(volunteer_id=vol1.id, shift_id=shift.id))
    create_signup(db, SignupCreate(volunteer_id=vol2.id, shift_id=shift.id))
    drop_signup(db, s1.id)

    active = get_active_signups_by_shift(db, shift.id)
    assert len(active) == 1
    assert active[0].volunteer_id == vol2.id


def test_duplicate_signup_raises_integrity_error(db: sqlite3.Connection):
    """Inserting duplicate (volunteer_id, shift_id) raises IntegrityError."""
    vol = _make_volunteer(db, phone="+5555")
    shift = _make_shift(db, d=date(2025, 8, 1))
    create_signup(db, SignupCreate(volunteer_id=vol.id, shift_id=shift.id))

    with pytest.raises(sqlite3.IntegrityError):
        create_signup(db, SignupCreate(volunteer_id=vol.id, shift_id=shift.id))
