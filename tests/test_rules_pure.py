"""Tests for pure validation rule functions — no DB, no fixtures."""

from datetime import date

from app.rules.pure import (
    RuleResult,
    SignupPhase,
    check_capacity,
    check_kakad_limit,
    check_phase1_total,
    check_phase2_additional,
    check_robe_limit,
    check_running_total,
    check_thursday_limit,
    get_applicable_rules,
    get_signup_phase,
)


# ---------------------------------------------------------------------------
# Phase determination
# ---------------------------------------------------------------------------

class TestGetSignupPhase:
    def test_15_days_before_is_phase1(self):
        month_start = date(2026, 3, 1)
        today = date(2026, 2, 14)  # 15 days before
        assert get_signup_phase(today, month_start) == SignupPhase.PHASE_1

    def test_exactly_14_days_before_is_phase1(self):
        month_start = date(2026, 3, 1)
        today = date(2026, 2, 15)  # 14 days before
        assert get_signup_phase(today, month_start) == SignupPhase.PHASE_1

    def test_7_days_before_is_phase2(self):
        month_start = date(2026, 3, 1)
        today = date(2026, 2, 22)  # 7 days before
        assert get_signup_phase(today, month_start) == SignupPhase.PHASE_2

    def test_exactly_7_days_before_is_phase2(self):
        month_start = date(2026, 3, 1)
        today = date(2026, 2, 22)  # exactly 7 days
        assert get_signup_phase(today, month_start) == SignupPhase.PHASE_2

    def test_6_days_before_is_mid_month(self):
        month_start = date(2026, 3, 1)
        today = date(2026, 2, 23)  # 6 days before
        assert get_signup_phase(today, month_start) == SignupPhase.MID_MONTH

    def test_day_of_month_start_is_mid_month(self):
        month_start = date(2026, 3, 1)
        today = date(2026, 3, 1)  # day of
        assert get_signup_phase(today, month_start) == SignupPhase.MID_MONTH


# ---------------------------------------------------------------------------
# Phase 1 rules
# ---------------------------------------------------------------------------

class TestPhase1Rules:
    def test_kakad_under_limit_ok(self):
        result = check_kakad_limit(1, max=2)
        assert result == RuleResult(True, "")

    def test_kakad_at_limit_rejected(self):
        result = check_kakad_limit(2, max=2)
        assert result.allowed is False
        assert "Kakad limit" in result.reason

    def test_robe_under_limit_ok(self):
        result = check_robe_limit(3, max=4)
        assert result == RuleResult(True, "")

    def test_robe_at_limit_rejected(self):
        result = check_robe_limit(4, max=4)
        assert result.allowed is False
        assert "Robe limit" in result.reason

    def test_thursday_under_limit_ok(self):
        result = check_thursday_limit(0, max=1)
        assert result == RuleResult(True, "")

    def test_thursday_at_limit_rejected(self):
        result = check_thursday_limit(1, max=1)
        assert result.allowed is False
        assert "Thursday limit" in result.reason

    def test_phase1_total_under_limit_ok(self):
        result = check_phase1_total(5, max=6)
        assert result == RuleResult(True, "")

    def test_phase1_total_at_limit_rejected(self):
        result = check_phase1_total(6, max=6)
        assert result.allowed is False
        assert "Phase 1 total limit" in result.reason


# ---------------------------------------------------------------------------
# Phase 2 rules
# ---------------------------------------------------------------------------

class TestPhase2Rules:
    def test_phase2_additional_under_limit_ok(self):
        result = check_phase2_additional(1, max=2)
        assert result == RuleResult(True, "")

    def test_phase2_additional_at_limit_rejected(self):
        result = check_phase2_additional(2, max=2)
        assert result.allowed is False
        assert "Phase 2 additional limit" in result.reason

    def test_running_total_under_limit_ok(self):
        result = check_running_total(7, max=8)
        assert result == RuleResult(True, "")

    def test_running_total_at_limit_rejected(self):
        result = check_running_total(8, max=8)
        assert result.allowed is False
        assert "Running total limit" in result.reason


# ---------------------------------------------------------------------------
# Capacity (always checked)
# ---------------------------------------------------------------------------

class TestCapacity:
    def test_capacity_available_ok(self):
        result = check_capacity(0, 1)
        assert result == RuleResult(True, "")

    def test_capacity_full_rejected(self):
        result = check_capacity(1, 1)
        assert result.allowed is False
        assert "full" in result.reason

    def test_capacity_partial_ok(self):
        result = check_capacity(2, 3)
        assert result == RuleResult(True, "")

    def test_capacity_at_limit_rejected(self):
        result = check_capacity(3, 3)
        assert result.allowed is False
        assert "full" in result.reason


# ---------------------------------------------------------------------------
# get_applicable_rules
# ---------------------------------------------------------------------------

class TestGetApplicableRules:
    def test_phase1_returns_4_rules(self):
        rules = get_applicable_rules(SignupPhase.PHASE_1)
        assert len(rules) == 4
        assert check_kakad_limit in rules
        assert check_robe_limit in rules
        assert check_thursday_limit in rules
        assert check_phase1_total in rules

    def test_phase2_returns_2_rules(self):
        rules = get_applicable_rules(SignupPhase.PHASE_2)
        assert len(rules) == 2
        assert check_phase2_additional in rules
        assert check_running_total in rules

    def test_mid_month_returns_empty(self):
        rules = get_applicable_rules(SignupPhase.MID_MONTH)
        assert rules == []
