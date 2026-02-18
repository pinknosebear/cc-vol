"""Pure validation rule functions — no DB, no app.models imports."""

from __future__ import annotations

from collections import namedtuple
from datetime import date
from enum import Enum


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

RuleResult = namedtuple("RuleResult", ["allowed", "reason"])


class SignupPhase(Enum):
    BLOCKED = "blocked"    # 14+ days before month: signups not open yet
    PHASE_1 = "phase_1"   # 7-13 days before: 2K + 4R + 1Thu, max 6
    PHASE_2 = "phase_2"   # 1-6 days before: running total raised to 8
    MID_MONTH = "mid_month"  # on/after month start: capacity only


# ---------------------------------------------------------------------------
# Phase determination
# ---------------------------------------------------------------------------

def get_signup_phase(today: date, shift_month_start: date) -> SignupPhase:
    """Determine signup phase based on days before the shift month starts.

    - 14+ days before month start → BLOCKED (signups not open yet)
    - 7-13 days before → PHASE_1 (2K + 4R + 1Thu, max 6)
    - 1-6 days before → PHASE_2 (running total raised to 8)
    - on/after month start → MID_MONTH (capacity only)
    """
    days_before = (shift_month_start - today).days
    if days_before >= 14:
        return SignupPhase.BLOCKED
    if days_before >= 7:
        return SignupPhase.PHASE_1
    if days_before > 0:
        return SignupPhase.PHASE_2
    return SignupPhase.MID_MONTH


# ---------------------------------------------------------------------------
# Phase 1 rules
# ---------------------------------------------------------------------------

def check_kakad_limit(kakad_count: int, max: int = 2) -> RuleResult:
    """Check that kakad signup count has not reached the limit."""
    if kakad_count >= max:
        return RuleResult(False, f"Kakad limit reached ({kakad_count}/{max})")
    return RuleResult(True, "")


def check_robe_limit(robe_count: int, max: int = 4) -> RuleResult:
    """Check that robe signup count has not reached the limit."""
    if robe_count >= max:
        return RuleResult(False, f"Robe limit reached ({robe_count}/{max})")
    return RuleResult(True, "")


def check_thursday_limit(thursday_count: int, max: int = 1) -> RuleResult:
    """Check that Thursday signup count has not reached the limit."""
    if thursday_count >= max:
        return RuleResult(False, f"Thursday limit reached ({thursday_count}/{max})")
    return RuleResult(True, "")


def check_phase1_total(total_count: int, max: int = 6) -> RuleResult:
    """Check that total Phase 1 signups have not reached the limit."""
    if total_count >= max:
        return RuleResult(False, f"Phase 1 total limit reached ({total_count}/{max})")
    return RuleResult(True, "")


# ---------------------------------------------------------------------------
# Phase 2 rules
# ---------------------------------------------------------------------------

def check_running_total(total_count: int, max: int = 8) -> RuleResult:
    """Check that the running total across phases has not reached the limit."""
    if total_count >= max:
        return RuleResult(False, f"Running total limit reached ({total_count}/{max})")
    return RuleResult(True, "")


# ---------------------------------------------------------------------------
# Always checked
# ---------------------------------------------------------------------------

def check_capacity(current_signups: int, capacity: int) -> RuleResult:
    """Check that a shift has not reached its capacity."""
    if current_signups >= capacity:
        return RuleResult(False, f"Shift is full ({current_signups}/{capacity})")
    return RuleResult(True, "")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_applicable_rules(phase: SignupPhase) -> list:
    """Return the list of rule functions applicable to the given phase.

    Note: check_capacity is always checked separately and not included here.
    """
    if phase == SignupPhase.PHASE_1:
        return [check_kakad_limit, check_robe_limit, check_thursday_limit, check_phase1_total]
    if phase == SignupPhase.PHASE_2:
        return [check_running_total]
    return []
