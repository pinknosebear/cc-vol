"""Tests that seeded signup scenarios produce expected rejections.

Seeds the DB with seed_signups(db, 2026, 2), then attempts signups that
should be rejected by various rules.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models.shift import get_shifts_by_date, get_shifts_by_month
from app.models.volunteer import get_volunteer_by_phone
from app.rules.validator import validate_signup
from app.seed import seed_signups


# ---------------------------------------------------------------------------
# Constants — Feb 2026
# ---------------------------------------------------------------------------

YEAR, MONTH = 2026, 2
MONTH_START = date(YEAR, MONTH, 1)
PHASE1_TODAY = MONTH_START - timedelta(days=15)  # 2026-01-17
PHASE2_TODAY = MONTH_START - timedelta(days=7)   # 2026-01-25


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_db(db):
    """Seed shifts, volunteers, and signups for Feb 2026."""
    seed_signups(db, YEAR, MONTH)
    return db


def _get_vol_id(db, phone: str) -> int:
    vol = get_volunteer_by_phone(db, phone)
    assert vol is not None, f"Volunteer with phone {phone} not found"
    return vol.id


def _find_shift(db, target_date: date, shift_type: str) -> int:
    """Return the shift ID for the given date and type."""
    shifts = get_shifts_by_date(db, target_date)
    for s in shifts:
        if s.type == shift_type:
            return s.id
    raise ValueError(f"No {shift_type} shift on {target_date}")


# ====================================================================
# Phase 1 rejections (today = 2026-01-17)
# ====================================================================

class TestPhase1Rejections:
    """Sonia (2K+4R=6) and Raghu (1 Thursday) are at Phase 1 limits."""

    def test_sonia_extra_kakad_rejected(self, seeded_db):
        """Sonia already has 2 Kakad — 3rd Kakad rejected."""
        db = seeded_db
        sonia_id = _get_vol_id(db, "1111111111")
        # Pick an unused kakad shift (day 20)
        shift_id = _find_shift(db, date(YEAR, MONTH, 20), "kakad")
        violations = validate_signup(db, sonia_id, shift_id, today=PHASE1_TODAY)
        assert len(violations) > 0
        reasons = [v.reason.lower() for v in violations]
        assert any("kakad" in r for r in reasons)

    def test_sonia_extra_robe_rejected(self, seeded_db):
        """Sonia already has 4 Robe — 5th Robe rejected."""
        db = seeded_db
        sonia_id = _get_vol_id(db, "1111111111")
        shift_id = _find_shift(db, date(YEAR, MONTH, 20), "robe")
        violations = validate_signup(db, sonia_id, shift_id, today=PHASE1_TODAY)
        assert len(violations) > 0
        reasons = [v.reason.lower() for v in violations]
        assert any("robe" in r for r in reasons)

    def test_sonia_any_shift_rejected_total(self, seeded_db):
        """Sonia at 6 total — any new shift rejected by total/phase limit."""
        db = seeded_db
        sonia_id = _get_vol_id(db, "1111111111")
        # Try a kakad on a new day
        shift_id = _find_shift(db, date(YEAR, MONTH, 21), "kakad")
        violations = validate_signup(db, sonia_id, shift_id, today=PHASE1_TODAY)
        assert len(violations) > 0
        reasons = [v.reason.lower() for v in violations]
        assert any("total" in r or "phase" in r for r in reasons)

    def test_raghu_second_thursday_rejected(self, seeded_db):
        """Raghu has 1 Thursday — 2nd Thursday rejected."""
        db = seeded_db
        raghu_id = _get_vol_id(db, "2222222222")
        # Feb 12 is also a Thursday
        shift_id = _find_shift(db, date(YEAR, MONTH, 12), "kakad")
        violations = validate_signup(db, raghu_id, shift_id, today=PHASE1_TODAY)
        assert len(violations) > 0
        reasons = [v.reason.lower() for v in violations]
        assert any("thursday" in r for r in reasons)


# ====================================================================
# Phase 2 rejections (today = 2026-01-25)
# ====================================================================

class TestPhase2Rejections:
    """Ganesh (6 Phase1 + 2 Phase2 = 8 total) is at the running total limit."""

    def test_ganesh_9th_signup_rejected(self, seeded_db):
        """Ganesh at 8 total — 9th rejected by running total."""
        db = seeded_db
        ganesh_id = _get_vol_id(db, "3333333333")
        # Pick an unused shift
        shift_id = _find_shift(db, date(YEAR, MONTH, 25), "robe")
        violations = validate_signup(db, ganesh_id, shift_id, today=PHASE2_TODAY)
        assert len(violations) > 0
        reasons = [v.reason.lower() for v in violations]
        assert any("total" in r or "running" in r for r in reasons)


# ====================================================================
# Always-checked: capacity
# ====================================================================

class TestCapacityRejections:
    """Shifts filled to capacity by seed data should reject new signups."""

    def test_full_shift_rejected(self, seeded_db):
        """A shift at capacity rejects new signups."""
        db = seeded_db
        # Day 1 kakad has capacity=1 and was filled by a filler volunteer
        shift_id = _find_shift(db, date(YEAR, MONTH, 1), "kakad")
        # Use a volunteer who is NOT already signed up for this shift
        bhawna_id = _get_vol_id(db, "5555555555")
        violations = validate_signup(db, bhawna_id, shift_id, today=PHASE1_TODAY)
        assert len(violations) > 0
        reasons = [v.reason.lower() for v in violations]
        assert any("capacity" in r or "full" in r for r in reasons)
