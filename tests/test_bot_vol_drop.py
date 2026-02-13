"""Tests for the volunteer drop command handler."""

from datetime import date

import pytest

from app.bot.auth import VolunteerContext
from app.bot.handlers.vol_drop import handle_drop
from app.db import create_tables, get_db_connection


@pytest.fixture()
def db():
    """Create an in-memory database with schema and seed data."""
    conn = get_db_connection(":memory:")
    create_tables(conn)

    # Seed a volunteer
    conn.execute(
        "INSERT INTO volunteers (id, phone, name) VALUES (1, '9999999999', 'Test Vol')"
    )
    # Seed a kakad shift on 2026-02-15
    conn.execute(
        "INSERT INTO shifts (id, date, shift_type, capacity) VALUES (10, '2026-02-15', 'kakad', 2)"
    )
    conn.commit()
    return conn


@pytest.fixture()
def ctx():
    """Return a VolunteerContext for the seeded volunteer."""
    return VolunteerContext(volunteer_id=1, phone="9999999999", is_coordinator=False)


class TestHandleDropSuccess:
    def test_successful_drop(self, db, ctx):
        # Create an active signup
        db.execute("INSERT INTO signups (id, volunteer_id, shift_id) VALUES (100, 1, 10)")
        db.commit()

        result = handle_drop(db, ctx, {"date": date(2026, 2, 15), "type": "kakad"})
        assert result == "Dropped kakad shift on 2026-02-15"

        # Verify signup was actually dropped
        row = db.execute("SELECT dropped_at FROM signups WHERE id = 100").fetchone()
        assert row["dropped_at"] is not None


class TestHandleDropNoShift:
    def test_no_matching_shift(self, db, ctx):
        result = handle_drop(db, ctx, {"date": date(2026, 3, 1), "type": "robe"})
        assert result == "No robe shift found on 2026-03-01"


class TestHandleDropNoSignup:
    def test_no_active_signup(self, db, ctx):
        # Shift exists but volunteer has no signup
        result = handle_drop(db, ctx, {"date": date(2026, 2, 15), "type": "kakad"})
        assert result == "You don't have an active signup for kakad on 2026-02-15"


class TestHandleDropAlreadyDropped:
    def test_already_dropped_signup(self, db, ctx):
        # Create a signup that is already dropped
        db.execute(
            "INSERT INTO signups (id, volunteer_id, shift_id, dropped_at) "
            "VALUES (101, 1, 10, '2026-02-14 08:00:00')"
        )
        db.commit()

        result = handle_drop(db, ctx, {"date": date(2026, 2, 15), "type": "kakad"})
        assert result == "You don't have an active signup for kakad on 2026-02-15"
