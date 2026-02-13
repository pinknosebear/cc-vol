"""Tests for volunteer query command handlers."""

from __future__ import annotations

from datetime import date

import pytest

from app.bot.auth import VolunteerContext
from app.bot.handlers.vol_query import handle_my_shifts, handle_shifts
from app.db import create_tables, get_db_connection


@pytest.fixture()
def db():
    conn = get_db_connection(":memory:")
    create_tables(conn)
    return conn


@pytest.fixture()
def context(db):
    """Insert a volunteer and return their context."""
    db.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        ("+1111111111", "Alice"),
    )
    db.commit()
    return VolunteerContext(volunteer_id=1, phone="+1111111111", is_coordinator=False)


def _insert_shift(db, shift_date: str, shift_type: str, capacity: int = 3) -> int:
    cur = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (shift_date, shift_type, capacity),
    )
    db.commit()
    return cur.lastrowid


def _insert_signup(db, volunteer_id: int, shift_id: int, dropped: bool = False):
    db.execute(
        "INSERT INTO signups (volunteer_id, shift_id, dropped_at) VALUES (?, ?, ?)",
        (volunteer_id, shift_id, "2026-01-15 00:00:00" if dropped else None),
    )
    db.commit()


class TestHandleMyShifts:
    def test_no_shifts_returns_empty_message(self, db, context):
        result = handle_my_shifts(db, context, {"month": "2026-01"})
        assert result == "You have no shifts for 2026-01"

    def test_two_shifts_returns_formatted_list(self, db, context):
        s1 = _insert_shift(db, "2026-01-10", "kakad")
        s2 = _insert_shift(db, "2026-01-12", "robe")
        _insert_signup(db, context.volunteer_id, s1)
        _insert_signup(db, context.volunteer_id, s2)

        result = handle_my_shifts(db, context, {"month": "2026-01"})

        assert "2026-01-10 kakad" in result
        assert "2026-01-12 robe" in result
        assert result.startswith("Your shifts for 2026-01:")


class TestHandleShifts:
    def test_no_shifts_returns_empty_message(self, db, context):
        result = handle_shifts(db, context, {"date": date(2026, 1, 10)})
        assert result == "No shifts found for 2026-01-10"

    def test_kakad_and_robe_shows_both_with_counts(self, db, context):
        s1 = _insert_shift(db, "2026-01-10", "kakad", capacity=3)
        s2 = _insert_shift(db, "2026-01-10", "robe", capacity=4)
        _insert_signup(db, context.volunteer_id, s1)
        _insert_signup(db, context.volunteer_id, s2)

        result = handle_shifts(db, context, {"date": date(2026, 1, 10)})

        assert "kakad: 1/3" in result
        assert "robe: 1/4" in result

    def test_excludes_dropped_signups_from_counts(self, db, context):
        s1 = _insert_shift(db, "2026-01-10", "kakad", capacity=3)
        _insert_signup(db, context.volunteer_id, s1, dropped=True)

        # Add another volunteer with active signup
        db.execute(
            "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
            ("+2222222222", "Bob"),
        )
        db.commit()
        _insert_signup(db, 2, s1, dropped=False)

        result = handle_shifts(db, context, {"date": date(2026, 1, 10)})

        assert "kakad: 1/3" in result
