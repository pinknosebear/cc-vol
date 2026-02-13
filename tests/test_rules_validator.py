"""Tests for the signup validation orchestrator."""

from __future__ import annotations

from datetime import date

import pytest

from app.db import get_db_connection, create_tables
from app.rules.validator import validate_signup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_volunteer(db, phone="1111111111", name="Test Vol"):
    db.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)", (phone, name)
    )
    db.commit()
    return db.execute(
        "SELECT id FROM volunteers WHERE phone = ?", (phone,)
    ).fetchone()["id"]


def _make_shift(db, dt: date, shift_type: str = "kakad", capacity: int = 3):
    db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (dt.isoformat(), shift_type, capacity),
    )
    db.commit()
    return db.execute(
        "SELECT id FROM shifts WHERE date = ? AND shift_type = ?",
        (dt.isoformat(), shift_type),
    ).fetchone()["id"]


def _make_signup(db, volunteer_id: int, shift_id: int, signed_up_at: str | None = None):
    """Create a signup, optionally backdating signed_up_at."""
    db.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    db.commit()
    sid = db.execute(
        "SELECT id FROM signups WHERE volunteer_id = ? AND shift_id = ?",
        (volunteer_id, shift_id),
    ).fetchone()["id"]
    if signed_up_at:
        db.execute(
            "UPDATE signups SET signed_up_at = ? WHERE id = ?",
            (signed_up_at, sid),
        )
        db.commit()
    return sid


# Shift month = March 2026.  Month start = 2026-03-01.
# Phase 1 today: 2026-02-14 (15 days before) → >= 14
# Phase 2 today: 2026-02-22 (7 days before)  → >= 7 and < 14
# Mid-month today: 2026-03-05                → < 7

MONTH_START = date(2026, 3, 1)
PHASE1_TODAY = date(2026, 2, 14)
PHASE2_TODAY = date(2026, 2, 22)
MID_MONTH_TODAY = date(2026, 3, 5)


@pytest.fixture
def db():
    conn = get_db_connection(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


# ====================================================================
# Phase 1 tests
# ====================================================================

class TestPhase1:
    """Phase 1: today = 2+ weeks before month start."""

    def test_kakad_limit_rejected(self, db):
        """2 kakad already -> 3rd kakad -> rejected."""
        vol = _make_volunteer(db)
        # Create 2 existing kakad signups on different days in March
        s1 = _make_shift(db, date(2026, 3, 2), "kakad", capacity=10)
        s2 = _make_shift(db, date(2026, 3, 3), "kakad", capacity=10)
        _make_signup(db, vol, s1)
        _make_signup(db, vol, s2)
        # Try a 3rd kakad
        s3 = _make_shift(db, date(2026, 3, 4), "kakad", capacity=10)
        violations = validate_signup(db, vol, s3, today=PHASE1_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("kakad" in r for r in reasons)

    def test_robe_limit_rejected(self, db):
        """4 robe already -> 5th robe -> rejected."""
        vol = _make_volunteer(db)
        for day in (2, 3, 4, 5):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
        s5 = _make_shift(db, date(2026, 3, 6), "robe", capacity=10)
        violations = validate_signup(db, vol, s5, today=PHASE1_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("robe" in r for r in reasons)

    def test_thursday_limit_rejected(self, db):
        """1 Thursday already -> 2nd Thursday -> rejected."""
        vol = _make_volunteer(db)
        # 2026-03-05 is a Thursday
        s1 = _make_shift(db, date(2026, 3, 5), "kakad", capacity=10)
        _make_signup(db, vol, s1)
        # 2026-03-12 is also a Thursday
        s2 = _make_shift(db, date(2026, 3, 12), "kakad", capacity=10)
        violations = validate_signup(db, vol, s2, today=PHASE1_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("thursday" in r for r in reasons)

    def test_phase1_total_rejected(self, db):
        """6 total (2K + 4R) -> 7th -> rejected."""
        vol = _make_volunteer(db)
        # 2 kakad
        for day in (2, 3):
            sid = _make_shift(db, date(2026, 3, day), "kakad", capacity=10)
            _make_signup(db, vol, sid)
        # 4 robe
        for day in (4, 5, 6, 7):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
        # 7th signup (robe on a new day)
        s7 = _make_shift(db, date(2026, 3, 9), "robe", capacity=10)
        violations = validate_signup(db, vol, s7, today=PHASE1_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("phase 1 total" in r for r in reasons)

    def test_same_day_kakad_and_robe_allowed(self, db):
        """Same-day kakad + robe -> allowed (different shift types)."""
        vol = _make_volunteer(db)
        sk = _make_shift(db, date(2026, 3, 2), "kakad", capacity=10)
        _make_signup(db, vol, sk)
        sr = _make_shift(db, date(2026, 3, 2), "robe", capacity=10)
        violations = validate_signup(db, vol, sr, today=PHASE1_TODAY)
        assert violations == []


# ====================================================================
# Phase 2 tests
# ====================================================================

class TestPhase2:
    """Phase 2: today = 1 week before month start."""

    def _seed_phase1_signups(self, db, vol, count=6):
        """Create `count` signups dated during Phase 1 window."""
        # Sign up during phase 1 (signed_up_at = PHASE1_TODAY)
        ids = []
        for i, day in enumerate(range(2, 2 + count)):
            stype = "kakad" if i < 2 else "robe"
            sid = _make_shift(db, date(2026, 3, day), stype, capacity=10)
            _make_signup(db, vol, sid, signed_up_at=PHASE1_TODAY.isoformat())
            ids.append(sid)
        return ids

    def test_phase2_first_additional_allowed(self, db):
        """6 from Phase 1, 0 Phase 2 -> new signup allowed."""
        vol = _make_volunteer(db)
        self._seed_phase1_signups(db, vol, 6)
        # New shift to sign up for in phase 2
        s_new = _make_shift(db, date(2026, 3, 10), "kakad", capacity=10)
        violations = validate_signup(db, vol, s_new, today=PHASE2_TODAY)
        assert violations == []

    def test_phase2_additional_rejected(self, db):
        """6 from Phase 1, 2 Phase 2 already -> rejected."""
        vol = _make_volunteer(db)
        self._seed_phase1_signups(db, vol, 6)
        # 2 phase-2 signups (signed up during phase 2 window)
        for day in (10, 11):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid, signed_up_at=PHASE2_TODAY.isoformat())
        # Try a 3rd phase-2 signup
        s_new = _make_shift(db, date(2026, 3, 12), "robe", capacity=10)
        violations = validate_signup(db, vol, s_new, today=PHASE2_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("phase 2 additional" in r for r in reasons)

    def test_running_total_rejected(self, db):
        """8 total -> rejected by running total."""
        vol = _make_volunteer(db)
        self._seed_phase1_signups(db, vol, 6)
        # 2 phase-2 signups
        for day in (10, 11):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid, signed_up_at=PHASE2_TODAY.isoformat())
        # Total is now 8 -> 9th should be rejected
        s_new = _make_shift(db, date(2026, 3, 13), "robe", capacity=10)
        violations = validate_signup(db, vol, s_new, today=PHASE2_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("running total" in r for r in reasons)


# ====================================================================
# Always-checked / edge case tests
# ====================================================================

class TestCapacityAndEdgeCases:

    def test_shift_at_capacity_rejected(self, db):
        """Shift at capacity -> rejected regardless of phase."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "kakad", capacity=1)
        other_vol = _make_volunteer(db, phone="2222222222", name="Other")
        _make_signup(db, other_vol, s)
        violations = validate_signup(db, vol, s, today=PHASE1_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("full" in r for r in reasons)

    def test_mid_month_only_checks_capacity(self, db):
        """Mid-month -> only capacity checked, other rules ignored."""
        vol = _make_volunteer(db)
        # Fill up 6 signups (would normally hit phase 1 total limit)
        for day in range(2, 8):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
        # 7th signup mid-month should be fine (no phase rules)
        s_new = _make_shift(db, date(2026, 3, 9), "robe", capacity=10)
        violations = validate_signup(db, vol, s_new, today=MID_MONTH_TODAY)
        assert violations == []

    def test_mid_month_capacity_still_enforced(self, db):
        """Mid-month still enforces capacity."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "kakad", capacity=1)
        other_vol = _make_volunteer(db, phone="3333333333", name="Filler")
        _make_signup(db, other_vol, s)
        violations = validate_signup(db, vol, s, today=MID_MONTH_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("full" in r for r in reasons)

    def test_drop_and_resign_allowed(self, db):
        """Drop a signup, then re-sign -> allowed (slot freed)."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "kakad", capacity=1)
        signup_id = _make_signup(db, vol, s)
        # Drop
        db.execute(
            "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE id = ?",
            (signup_id,),
        )
        db.commit()
        # Now the shift has 0 active signups; re-sign with a new volunteer
        vol2 = _make_volunteer(db, phone="4444444444", name="New Vol")
        violations = validate_signup(db, vol2, s, today=PHASE1_TODAY)
        assert violations == []

    def test_fresh_volunteer_all_valid(self, db):
        """Fresh volunteer with no signups -> everything valid."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "kakad", capacity=10)
        violations = validate_signup(db, vol, s, today=PHASE1_TODAY)
        assert violations == []
