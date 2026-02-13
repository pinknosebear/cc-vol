"""Tests for GET /api/coordinator/status endpoint."""

from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db_connection, create_tables


def _make_client():
    """Create a test client with a fresh in-memory DB.

    Uses check_same_thread=False since TestClient runs the app in a
    separate thread from the test code that seeds data.
    """
    import sqlite3

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    app.state.db = conn
    return TestClient(app), conn


def _seed_shift(conn, shift_date: str, shift_type: str, capacity: int) -> int:
    """Insert a shift and return its id."""
    cursor = conn.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (shift_date, shift_type, capacity),
    )
    conn.commit()
    return cursor.lastrowid


def _seed_volunteer(conn, phone: str, name: str) -> int:
    """Insert a volunteer and return their id."""
    cursor = conn.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        (phone, name),
    )
    conn.commit()
    return cursor.lastrowid


def _seed_signup(conn, volunteer_id: int, shift_id: int):
    """Insert an active signup."""
    conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    conn.commit()


class TestCoordinatorStatus:
    """Tests for GET /api/coordinator/status."""

    def test_returns_shifts_with_correct_fill_calculations(self):
        client, conn = _make_client()

        # Create a shift with capacity 2
        shift_id = _seed_shift(conn, "2026-02-15", "kakad", 2)

        # Add 1 volunteer signup
        vol_id = _seed_volunteer(conn, "+1111111111", "Alice")
        _seed_signup(conn, vol_id, shift_id)

        resp = client.get("/api/coordinator/status?date=2026-02-15")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == shift_id
        assert data[0]["date"] == "2026-02-15"
        assert data[0]["type"] == "kakad"
        assert data[0]["capacity"] == 2
        assert data[0]["signup_count"] == 1
        assert data[0]["status"] == "open"

    def test_filled_shift(self):
        client, conn = _make_client()

        shift_id = _seed_shift(conn, "2026-02-15", "robe", 2)
        v1 = _seed_volunteer(conn, "+2222222222", "Bob")
        v2 = _seed_volunteer(conn, "+3333333333", "Carol")
        _seed_signup(conn, v1, shift_id)
        _seed_signup(conn, v2, shift_id)

        resp = client.get("/api/coordinator/status?date=2026-02-15")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["signup_count"] == 2
        assert data[0]["status"] == "filled"

    def test_dropped_signups_not_counted(self):
        client, conn = _make_client()

        shift_id = _seed_shift(conn, "2026-02-15", "kakad", 2)
        v1 = _seed_volunteer(conn, "+4444444444", "Dave")
        _seed_signup(conn, v1, shift_id)
        # Drop the signup
        conn.execute(
            "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE volunteer_id = ? AND shift_id = ?",
            (v1, shift_id),
        )
        conn.commit()

        resp = client.get("/api/coordinator/status?date=2026-02-15")
        data = resp.json()
        assert data[0]["signup_count"] == 0
        assert data[0]["status"] == "open"

    def test_multiple_shifts_on_same_date(self):
        client, conn = _make_client()

        s1 = _seed_shift(conn, "2026-02-15", "kakad", 3)
        s2 = _seed_shift(conn, "2026-02-15", "robe", 4)

        resp = client.get("/api/coordinator/status?date=2026-02-15")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        types = {d["type"] for d in data}
        assert types == {"kakad", "robe"}

    def test_missing_date_defaults_to_today(self):
        client, conn = _make_client()

        today = date.today().isoformat()
        _seed_shift(conn, today, "kakad", 2)

        resp = client.get("/api/coordinator/status")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == today

    def test_no_shifts_returns_empty_list(self):
        client, _ = _make_client()

        resp = client.get("/api/coordinator/status?date=2026-03-01")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_invalid_date_returns_400(self):
        client, _ = _make_client()

        resp = client.get("/api/coordinator/status?date=not-a-date")
        assert resp.status_code == 400
        assert "Invalid date" in resp.json()["detail"]

    def test_invalid_date_partial_format(self):
        client, _ = _make_client()

        resp = client.get("/api/coordinator/status?date=2026-13-01")
        assert resp.status_code == 400
