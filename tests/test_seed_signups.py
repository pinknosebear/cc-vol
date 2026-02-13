"""Tests that verify the seeded signup state for Feb 2026."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.shift import get_shifts_by_date
from app.models.signup import (
    get_active_signups_by_shift,
    get_signups_by_volunteer,
)
from app.models.volunteer import get_volunteer_by_phone
from app.seed import seed_signups


@pytest.fixture
def seeded_db(db):
    """Seed shifts, volunteers, and signups for Feb 2026."""
    seed_signups(db, 2026, 2)
    return db


# ---- Sonia: 2 Kakad + 4 Robe = 6 active signups ----

def test_sonia_has_6_active_signups(seeded_db):
    vol = get_volunteer_by_phone(seeded_db, "1111111111")
    assert vol is not None
    signups = get_signups_by_volunteer(seeded_db, vol.id, "2026-02")
    active = [s for s in signups if s.dropped_at is None]
    assert len(active) == 6


def test_sonia_has_2_kakad_and_4_robe(seeded_db):
    vol = get_volunteer_by_phone(seeded_db, "1111111111")
    assert vol is not None
    signups = get_signups_by_volunteer(seeded_db, vol.id, "2026-02")
    active = [s for s in signups if s.dropped_at is None]

    # Resolve shift types
    kakad_count = 0
    robe_count = 0
    for s in active:
        row = seeded_db.execute(
            "SELECT shift_type FROM shifts WHERE id = ?", (s.shift_id,)
        ).fetchone()
        if row["shift_type"] == "kakad":
            kakad_count += 1
        elif row["shift_type"] == "robe":
            robe_count += 1

    assert kakad_count == 2
    assert robe_count == 4


# ---- Raghu: exactly 1 Thursday shift ----

def test_raghu_has_1_thursday_shift(seeded_db):
    vol = get_volunteer_by_phone(seeded_db, "2222222222")
    assert vol is not None
    signups = get_signups_by_volunteer(seeded_db, vol.id, "2026-02")
    active = [s for s in signups if s.dropped_at is None]
    assert len(active) == 1

    # Verify it's a Thursday
    row = seeded_db.execute(
        "SELECT date FROM shifts WHERE id = ?", (active[0].shift_id,)
    ).fetchone()
    shift_date = date.fromisoformat(row["date"])
    assert shift_date.weekday() == 3, f"Expected Thursday (3), got {shift_date.weekday()}"


# ---- Ganesh: 8 total active signups (6 Phase 1 + 2 Phase 2) ----

def test_ganesh_has_8_active_signups(seeded_db):
    vol = get_volunteer_by_phone(seeded_db, "3333333333")
    assert vol is not None
    signups = get_signups_by_volunteer(seeded_db, vol.id, "2026-02")
    active = [s for s in signups if s.dropped_at is None]
    assert len(active) == 8


# ---- Anita: at least 1 dropped signup, plus active ones ----

def test_anita_has_dropped_and_active_signups(seeded_db):
    vol = get_volunteer_by_phone(seeded_db, "4444444444")
    assert vol is not None
    signups = get_signups_by_volunteer(seeded_db, vol.id, "2026-02")
    active = [s for s in signups if s.dropped_at is None]
    dropped = [s for s in signups if s.dropped_at is not None]
    assert len(dropped) >= 1, "Anita should have at least 1 dropped signup"
    assert len(active) >= 1, "Anita should have at least 1 active signup"


# ---- Bhawna: exactly 1 active signup ----

def test_bhawna_has_1_active_signup(seeded_db):
    vol = get_volunteer_by_phone(seeded_db, "5555555555")
    assert vol is not None
    signups = get_signups_by_volunteer(seeded_db, vol.id, "2026-02")
    active = [s for s in signups if s.dropped_at is None]
    assert len(active) == 1


# ---- Last few days (25-28): 0 signups ----

def test_last_days_have_no_signups(seeded_db):
    for day in range(25, 29):
        shifts = get_shifts_by_date(seeded_db, date(2026, 2, day))
        for sh in shifts:
            active = get_active_signups_by_shift(seeded_db, sh.id)
            assert len(active) == 0, (
                f"Day {day} {sh.type} should have 0 signups, got {len(active)}"
            )


# ---- First couple days (1-2): shifts are staffed ----

def test_first_days_are_staffed(seeded_db):
    for day in [1, 2]:
        shifts = get_shifts_by_date(seeded_db, date(2026, 2, day))
        assert len(shifts) > 0, f"Day {day} should have shifts"
        for sh in shifts:
            active = get_active_signups_by_shift(seeded_db, sh.id)
            assert len(active) > 0, (
                f"Day {day} {sh.type} should have signups, got 0"
            )
