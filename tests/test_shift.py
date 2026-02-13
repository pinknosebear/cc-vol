"""Tests for the shift domain model."""

import sqlite3
from datetime import date

import pytest

from app.models.shift import (
    Shift,
    ShiftCreate,
    create_shift,
    get_robe_capacity,
    get_shifts_by_date,
    get_shifts_by_month,
)


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

def test_create_shift_returns_all_fields(db: sqlite3.Connection):
    """Create a shift and verify all returned fields."""
    data = ShiftCreate(date=date(2025, 6, 15), type="kakad", capacity=1)
    shift = create_shift(db, data)

    assert isinstance(shift, Shift)
    assert shift.id is not None
    assert shift.date == date(2025, 6, 15)
    assert shift.type == "kakad"
    assert shift.capacity == 1
    assert shift.created_at is not None


def test_get_shifts_by_date_returns_correct_shifts(db: sqlite3.Connection):
    """get_shifts_by_date returns the shifts for that date."""
    target = date(2025, 7, 1)
    create_shift(db, ShiftCreate(date=target, type="kakad", capacity=1))
    create_shift(db, ShiftCreate(date=target, type="robe", capacity=3))
    # Different date — should not appear
    create_shift(db, ShiftCreate(date=date(2025, 7, 2), type="kakad", capacity=1))

    shifts = get_shifts_by_date(db, target)
    assert len(shifts) == 2
    types = {s.type for s in shifts}
    assert types == {"kakad", "robe"}


def test_get_shifts_by_date_empty(db: sqlite3.Connection):
    """get_shifts_by_date returns empty list when no shifts exist for date."""
    shifts = get_shifts_by_date(db, date(2025, 12, 25))
    assert shifts == []


def test_get_shifts_by_month_returns_all_in_month(db: sqlite3.Connection):
    """get_shifts_by_month returns every shift in the given month."""
    create_shift(db, ShiftCreate(date=date(2025, 8, 1), type="kakad", capacity=1))
    create_shift(db, ShiftCreate(date=date(2025, 8, 15), type="robe", capacity=3))
    create_shift(db, ShiftCreate(date=date(2025, 8, 31), type="kakad", capacity=1))
    # Different month — should not appear
    create_shift(db, ShiftCreate(date=date(2025, 9, 1), type="kakad", capacity=1))

    shifts = get_shifts_by_month(db, 2025, 8)
    assert len(shifts) == 3
    assert all(s.date.month == 8 for s in shifts)


def test_duplicate_date_type_raises_integrity_error(db: sqlite3.Connection):
    """Inserting duplicate (date, type) raises IntegrityError."""
    data = ShiftCreate(date=date(2025, 6, 20), type="robe", capacity=3)
    create_shift(db, data)
    with pytest.raises(sqlite3.IntegrityError):
        create_shift(db, data)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

def test_get_robe_capacity_returns_3():
    """Capacity is 3 on Sun(6), Mon(0), Wed(2), Fri(4)."""
    for weekday in (0, 2, 4, 6):
        assert get_robe_capacity(weekday) == 3, f"Expected 3 for weekday={weekday}"


def test_get_robe_capacity_returns_4():
    """Capacity is 4 on Tue(1), Thu(3), Sat(5)."""
    for weekday in (1, 3, 5):
        assert get_robe_capacity(weekday) == 4, f"Expected 4 for weekday={weekday}"
