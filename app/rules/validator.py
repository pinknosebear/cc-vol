"""Signup validation orchestrator.

Combines query-layer counts with pure rule functions into a single
``validate_signup`` entry-point that returns a list of violations.
"""

from __future__ import annotations

import sqlite3
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
    get_signup_phase,
)
from app.rules.queries import (
    get_kakad_count,
    get_phase2_count,
    get_robe_count,
    get_shift_capacity,
    get_shift_signup_count,
    get_thursday_count,
    get_total_count,
)


def _get_shift_details(db: sqlite3.Connection, shift_id: int) -> dict:
    """Fetch shift date, shift_type, and capacity from the DB."""
    row = db.execute(
        "SELECT date, shift_type, capacity FROM shifts WHERE id = ?",
        (shift_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Shift {shift_id} not found")
    return {
        "date": date.fromisoformat(row["date"]),
        "shift_type": row["shift_type"],
        "capacity": row["capacity"],
    }


def validate_signup(
    db: sqlite3.Connection,
    volunteer_id: int,
    shift_id: int,
    today: date | None = None,
) -> list[RuleResult]:
    """Validate a signup attempt and return a list of violations.

    An empty list means the signup is allowed.
    """
    # Check if volunteer is approved
    volunteer = db.execute(
        "SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)
    ).fetchone()
    if volunteer is None or volunteer["status"] != "approved":
        return [
            RuleResult(
                allowed=False,
                reason="Volunteer is not approved to sign up",
            )
        ]

    shift = _get_shift_details(db, shift_id)
    shift_date: date = shift["date"]
    shift_type: str = shift["shift_type"]
    capacity: int = shift["capacity"]

    month_start = shift_date.replace(day=1)
    year, month = month_start.year, month_start.month

    effective_today = today or date.today()
    phase = get_signup_phase(effective_today, month_start)

    violations: list[RuleResult] = []

    # --- Capacity is always checked ---
    shift_signups = get_shift_signup_count(db, shift_id)
    cap_result = check_capacity(shift_signups, capacity)
    if not cap_result.allowed:
        violations.append(cap_result)

    # Mid-month: only capacity matters
    if phase == SignupPhase.MID_MONTH:
        return violations

    # --- Phase 1 rules ---
    if phase == SignupPhase.PHASE_1:
        total = get_total_count(db, volunteer_id, year, month)
        r = check_phase1_total(total)
        if not r.allowed:
            violations.append(r)

        if shift_type == "kakad":
            kakad = get_kakad_count(db, volunteer_id, year, month)
            r = check_kakad_limit(kakad)
            if not r.allowed:
                violations.append(r)

        if shift_type == "robe":
            robe = get_robe_count(db, volunteer_id, year, month)
            r = check_robe_limit(robe)
            if not r.allowed:
                violations.append(r)

        # Thursday limit only when shift is on a Thursday
        if shift_date.weekday() == 3:  # 3 = Thursday
            thurs = get_thursday_count(db, volunteer_id, year, month)
            r = check_thursday_limit(thurs)
            if not r.allowed:
                violations.append(r)

    # --- Phase 2 rules ---
    if phase == SignupPhase.PHASE_2:
        phase2 = get_phase2_count(db, volunteer_id, year, month)
        r = check_phase2_additional(phase2)
        if not r.allowed:
            violations.append(r)

        total = get_total_count(db, volunteer_id, year, month)
        r = check_running_total(total)
        if not r.allowed:
            violations.append(r)

    return violations
