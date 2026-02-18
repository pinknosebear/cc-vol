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


def _make_signup(db, volunteer_id: int, shift_id: int):
    db.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    db.commit()
    return db.execute(
        "SELECT id FROM signups WHERE volunteer_id = ? AND shift_id = ?",
        (volunteer_id, shift_id),
    ).fetchone()["id"]


# Shift month = March 2026. Month start = 2026-03-01.
#
# New phase boundaries:
#   BLOCKED:    14+ days before  → today <= 2026-02-15
#   PHASE_1:    7-13 days before → 2026-02-16 to 2026-02-22
#   PHASE_2:    1-6 days before  → 2026-02-23 to 2026-02-28
#   MID_MONTH:  on/after start   → 2026-03-01+

MONTH_START = date(2026, 3, 1)
BLOCKED_TODAY = date(2026, 2, 14)    # 15 days before — signups not open
PHASE1_TODAY = date(2026, 2, 22)     # 7 days before — Phase 1 window
PHASE2_TODAY = date(2026, 2, 25)     # 4 days before — Phase 2 window
MID_MONTH_TODAY = date(2026, 3, 5)   # after month start


@pytest.fixture
def db():
    conn = get_db_connection(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


# ====================================================================
# Blocked phase tests
# ====================================================================

class TestBlocked:
    def test_signup_before_window_opens_rejected(self, db):
        """Signup attempt 15 days before month start is blocked."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "kakad", capacity=10)
        violations = validate_signup(db, vol, s, today=BLOCKED_TODAY)
        assert len(violations) == 1
        assert "not open yet" in violations[0].reason.lower()


# ====================================================================
# Phase 1 tests
# ====================================================================

class TestPhase1:
    """Phase 1: 7-13 days before month start."""

    def test_kakad_limit_rejected(self, db):
        """2 kakad already -> 3rd kakad -> rejected."""
        vol = _make_volunteer(db)
        s1 = _make_shift(db, date(2026, 3, 2), "kakad", capacity=10)
        s2 = _make_shift(db, date(2026, 3, 3), "kakad", capacity=10)
        _make_signup(db, vol, s1)
        _make_signup(db, vol, s2)
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
        for day in (2, 3):
            sid = _make_shift(db, date(2026, 3, day), "kakad", capacity=10)
            _make_signup(db, vol, sid)
        for day in (4, 5, 6, 7):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
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

    def test_fresh_volunteer_all_valid(self, db):
        """Fresh volunteer with no signups -> allowed."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "kakad", capacity=10)
        violations = validate_signup(db, vol, s, today=PHASE1_TODAY)
        assert violations == []


# ====================================================================
# Phase 2 tests
# ====================================================================

class TestPhase2:
    """Phase 2: 1-6 days before month start. Ceiling raised to 8 total."""

    def test_phase2_allows_signups_up_to_8(self, db):
        """6 total signups -> 7th allowed in Phase 2."""
        vol = _make_volunteer(db)
        for day in (2, 3):
            sid = _make_shift(db, date(2026, 3, day), "kakad", capacity=10)
            _make_signup(db, vol, sid)
        for day in (4, 5, 6, 7):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
        s_new = _make_shift(db, date(2026, 3, 10), "robe", capacity=10)
        violations = validate_signup(db, vol, s_new, today=PHASE2_TODAY)
        assert violations == []

    def test_phase2_no_per_type_limits(self, db):
        """Phase 2 has no per-type limits — can sign up beyond 4 robe."""
        vol = _make_volunteer(db)
        for day in (2, 3, 4, 5):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
        s5 = _make_shift(db, date(2026, 3, 6), "robe", capacity=10)
        violations = validate_signup(db, vol, s5, today=PHASE2_TODAY)
        assert violations == []

    def test_phase2_running_total_rejected(self, db):
        """8 total -> 9th rejected."""
        vol = _make_volunteer(db)
        for day in (2, 3, 4, 5, 6, 7, 9, 10):
            stype = "kakad" if day <= 3 else "robe"
            sid = _make_shift(db, date(2026, 3, day), stype, capacity=10)
            _make_signup(db, vol, sid)
        s_new = _make_shift(db, date(2026, 3, 11), "robe", capacity=10)
        violations = validate_signup(db, vol, s_new, today=PHASE2_TODAY)
        reasons = [v.reason.lower() for v in violations]
        assert any("running total" in r for r in reasons)

    def test_phase2_volunteer_with_0_phase1_signups_can_sign_up(self, db):
        """Volunteer who missed Phase 1 can still sign up in Phase 2."""
        vol = _make_volunteer(db)
        s = _make_shift(db, date(2026, 3, 2), "robe", capacity=10)
        violations = validate_signup(db, vol, s, today=PHASE2_TODAY)
        assert violations == []


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
        """Mid-month -> only capacity checked, phase rules ignored."""
        vol = _make_volunteer(db)
        for day in range(2, 10):
            sid = _make_shift(db, date(2026, 3, day), "robe", capacity=10)
            _make_signup(db, vol, sid)
        s_new = _make_shift(db, date(2026, 3, 11), "robe", capacity=10)
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
        db.execute(
            "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE id = ?",
            (signup_id,),
        )
        db.commit()
        vol2 = _make_volunteer(db, phone="4444444444", name="New Vol")
        violations = validate_signup(db, vol2, s, today=PHASE1_TODAY)
        assert violations == []
