"""Tests for app.rules.queries — DB query layer for rule counts."""

from __future__ import annotations

import pytest
from datetime import date, timedelta
from typing import Optional

from app.rules.queries import (
    get_kakad_count,
    get_robe_count,
    get_total_count,
    get_thursday_count,
    get_phase2_count,
    get_shift_signup_count,
    get_shift_capacity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_volunteer(db, phone: str, name: str) -> int:
    cursor = db.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)", (phone, name)
    )
    db.commit()
    return cursor.lastrowid


def _insert_shift(db, dt: str, shift_type: str, capacity: int = 3) -> int:
    cursor = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (dt, shift_type, capacity),
    )
    db.commit()
    return cursor.lastrowid


def _insert_signup(db, volunteer_id: int, shift_id: int, signed_up_at: Optional[str] = None) -> int:
    if signed_up_at:
        cursor = db.execute(
            "INSERT INTO signups (volunteer_id, shift_id, signed_up_at) VALUES (?, ?, ?)",
            (volunteer_id, shift_id, signed_up_at),
        )
    else:
        cursor = db.execute(
            "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
            (volunteer_id, shift_id),
        )
    db.commit()
    return cursor.lastrowid


def _drop_signup(db, signup_id: int) -> None:
    db.execute(
        "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE id = ?",
        (signup_id,),
    )
    db.commit()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def setup(db):
    """Create a volunteer and various shifts/signups for Feb 2026."""
    vol_id = _insert_volunteer(db, "+1000", "Test Vol")

    # 2 kakad shifts in Feb 2026
    k1 = _insert_shift(db, "2026-02-02", "kakad", capacity=3)  # Mon
    k2 = _insert_shift(db, "2026-02-09", "kakad", capacity=3)  # Mon

    # 3 robe shifts in Feb 2026
    r1 = _insert_shift(db, "2026-02-03", "robe", capacity=4)   # Tue
    r2 = _insert_shift(db, "2026-02-05", "robe", capacity=3)   # Thu
    r3 = _insert_shift(db, "2026-02-10", "robe", capacity=3)   # Tue

    # 1 shift on Thursday (2026-02-05 is a Thursday)
    # r2 above is already on Thursday

    # Sign up for all 5
    s1 = _insert_signup(db, vol_id, k1)
    s2 = _insert_signup(db, vol_id, k2)
    s3 = _insert_signup(db, vol_id, r1)
    s4 = _insert_signup(db, vol_id, r2)  # Thursday robe
    s5 = _insert_signup(db, vol_id, r3)

    # A dropped signup (kakad) — should not be counted
    k3 = _insert_shift(db, "2026-02-16", "kakad", capacity=3)
    s6 = _insert_signup(db, vol_id, k3)
    _drop_signup(db, s6)

    # Another volunteer with signups on r1 for shift_signup_count test
    vol2 = _insert_volunteer(db, "+2000", "Vol Two")
    _insert_signup(db, vol2, r1)

    return {
        "db": db,
        "vol_id": vol_id,
        "vol2_id": vol2,
        "shifts": {"k1": k1, "k2": k2, "r1": r1, "r2": r2, "r3": r3, "k3": k3},
        "signups": {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_kakad_count(setup):
    assert get_kakad_count(setup["db"], setup["vol_id"], 2026, 2) == 2


def test_robe_count(setup):
    assert get_robe_count(setup["db"], setup["vol_id"], 2026, 2) == 3


def test_total_count(setup):
    # 2 kakad + 3 robe = 5 (dropped not counted)
    assert get_total_count(setup["db"], setup["vol_id"], 2026, 2) == 5


def test_thursday_count(setup):
    # Only r2 (2026-02-05, Thursday)
    assert get_thursday_count(setup["db"], setup["vol_id"], 2026, 2) == 1


def test_dropped_not_counted(setup):
    # k3 signup was dropped, so kakad should still be 2
    assert get_kakad_count(setup["db"], setup["vol_id"], 2026, 2) == 2
    assert get_total_count(setup["db"], setup["vol_id"], 2026, 2) == 5


def test_shift_signup_count(setup):
    # r1 has 2 signups (vol_id and vol2_id)
    assert get_shift_signup_count(setup["db"], setup["shifts"]["r1"]) == 2


def test_shift_capacity(setup):
    assert get_shift_capacity(setup["db"], setup["shifts"]["r1"]) == 4
    assert get_shift_capacity(setup["db"], setup["shifts"]["k1"]) == 3


def test_shift_capacity_not_found(setup):
    with pytest.raises(ValueError, match="Shift 9999 not found"):
        get_shift_capacity(setup["db"], 9999)


def test_phase2_count(setup):
    """Signups created during Phase 2 window (7-13 days before month start)."""
    db = setup["db"]
    vol_id = setup["vol_id"]

    # Phase 2 for March 2026: signed_up_at between Feb 16 and Feb 22 inclusive
    # Create shifts in March
    m1 = _insert_shift(db, "2026-03-02", "kakad", capacity=3)
    m2 = _insert_shift(db, "2026-03-03", "robe", capacity=3)

    # Signup during Phase 2 window
    _insert_signup(db, vol_id, m1, signed_up_at="2026-02-18 10:00:00")
    _insert_signup(db, vol_id, m2, signed_up_at="2026-02-20 10:00:00")

    assert get_phase2_count(db, vol_id, 2026, 3) == 2


def test_phase2_count_excludes_outside_window(setup):
    """Signups outside Phase 2 window should not be counted."""
    db = setup["db"]
    vol3 = _insert_volunteer(db, "+3000", "Vol Three")

    m1 = _insert_shift(db, "2026-03-05", "kakad", capacity=3)
    m2 = _insert_shift(db, "2026-03-06", "robe", capacity=3)

    # Phase 1 signup (too early — 15 days before)
    _insert_signup(db, vol3, m1, signed_up_at="2026-02-14 10:00:00")
    # Mid-month signup (too late — 5 days before)
    _insert_signup(db, vol3, m2, signed_up_at="2026-02-24 10:00:00")

    assert get_phase2_count(db, vol3, 2026, 3) == 0
