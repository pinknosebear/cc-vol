"""Tests for GET /api/shifts/{date} — day detail endpoint."""

from fastapi.testclient import TestClient

from app.main import app
from app.db import create_tables

import sqlite3

# Set up in-memory test DB (check_same_thread=False needed for FastAPI threadpool)
test_conn = sqlite3.connect(":memory:", check_same_thread=False)
test_conn.row_factory = sqlite3.Row
test_conn.execute("PRAGMA foreign_keys = ON")
create_tables(test_conn)
app.state.db = test_conn

client = TestClient(app)


def _reset_db():
    """Clear all data between tests."""
    test_conn.execute("DELETE FROM signups")
    test_conn.execute("DELETE FROM shifts")
    test_conn.execute("DELETE FROM volunteers")
    test_conn.commit()


def _seed_shift(date: str, shift_type: str, capacity: int) -> int:
    cursor = test_conn.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (date, shift_type, capacity),
    )
    test_conn.commit()
    return cursor.lastrowid


def _seed_volunteer(phone: str, name: str) -> int:
    cursor = test_conn.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        (phone, name),
    )
    test_conn.commit()
    return cursor.lastrowid


def _seed_signup(volunteer_id: int, shift_id: int) -> int:
    cursor = test_conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    test_conn.commit()
    return cursor.lastrowid


class TestDayDetail:
    def setup_method(self):
        _reset_db()

    def test_valid_date_returns_shifts_with_volunteers(self):
        """Shifts with active signups return volunteer details."""
        sid = _seed_shift("2026-01-05", "kakad", 2)
        v1 = _seed_volunteer("+910001", "Alice")
        v2 = _seed_volunteer("+910002", "Bob")
        _seed_signup(v1, sid)
        _seed_signup(v2, sid)

        resp = client.get("/api/shifts/2026-01-05")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        shift = data[0]
        assert shift["id"] == sid
        assert shift["date"] == "2026-01-05"
        assert shift["type"] == "kakad"
        assert shift["capacity"] == 2
        assert len(shift["volunteers"]) == 2
        names = {v["name"] for v in shift["volunteers"]}
        assert names == {"Alice", "Bob"}

    def test_dropped_signups_excluded(self):
        """Dropped signups should not appear in the volunteer list."""
        sid = _seed_shift("2026-01-06", "robe", 3)
        v1 = _seed_volunteer("+910003", "Carol")
        signup_id = _seed_signup(v1, sid)
        # Drop the signup
        test_conn.execute(
            "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE id = ?",
            (signup_id,),
        )
        test_conn.commit()

        resp = client.get("/api/shifts/2026-01-06")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["volunteers"] == []

    def test_date_with_no_shifts_returns_empty(self):
        """A date with no shifts returns an empty array."""
        resp = client.get("/api/shifts/2026-02-28")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_date_format_returns_422(self):
        """Non-date string in path returns 422."""
        resp = client.get("/api/shifts/not-a-date")
        assert resp.status_code == 422

    def test_multiple_shifts_same_day(self):
        """A day with both kakad and robe shifts returns both."""
        sid1 = _seed_shift("2026-01-07", "kakad", 2)
        sid2 = _seed_shift("2026-01-07", "robe", 3)
        v1 = _seed_volunteer("+910004", "Dan")
        _seed_signup(v1, sid1)

        resp = client.get("/api/shifts/2026-01-07")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        types = {s["type"] for s in data}
        assert types == {"kakad", "robe"}
        # Dan only signed up for kakad
        kakad = next(s for s in data if s["type"] == "kakad")
        robe = next(s for s in data if s["type"] == "robe")
        assert len(kakad["volunteers"]) == 1
        assert kakad["volunteers"][0]["name"] == "Dan"
        assert robe["volunteers"] == []
