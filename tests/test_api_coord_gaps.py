"""Tests for GET /api/coordinator/gaps endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db_connection, create_tables
from app.main import app


@pytest.fixture
def client():
    """Create a test client with an in-memory DB."""
    import sqlite3 as _sqlite3

    conn = _sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = _sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    app.state.db = conn
    yield TestClient(app)
    conn.close()


def _insert_shift(conn, date: str, shift_type: str, capacity: int) -> int:
    cursor = conn.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (date, shift_type, capacity),
    )
    conn.commit()
    return cursor.lastrowid


def _insert_volunteer(conn, phone: str, name: str) -> int:
    cursor = conn.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        (phone, name),
    )
    conn.commit()
    return cursor.lastrowid


def _insert_signup(conn, volunteer_id: int, shift_id: int):
    conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    conn.commit()


class TestGetGaps:
    def test_returns_only_unfilled_shifts(self, client):
        """Shifts with signup_count < capacity should appear in gaps."""
        db = app.state.db
        # Shift with capacity 3, only 1 signup -> gap
        sid = _insert_shift(db, "2026-02-10", "kakad", 3)
        vid = _insert_volunteer(db, "+1111111111", "Alice")
        _insert_signup(db, vid, sid)

        resp = client.get("/api/coordinator/gaps?month=2026-02")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == sid
        assert data[0]["signup_count"] == 1
        assert data[0]["gap_size"] == 2

    def test_fully_filled_shifts_excluded(self, client):
        """Shifts where signup_count == capacity should NOT appear."""
        db = app.state.db
        sid = _insert_shift(db, "2026-02-10", "robe", 2)
        v1 = _insert_volunteer(db, "+2222222221", "Bob")
        v2 = _insert_volunteer(db, "+2222222222", "Carol")
        _insert_signup(db, v1, sid)
        _insert_signup(db, v2, sid)

        resp = client.get("/api/coordinator/gaps?month=2026-02")
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_correct_gap_size_calculation(self, client):
        """gap_size should equal capacity - signup_count."""
        db = app.state.db
        sid = _insert_shift(db, "2026-02-15", "kakad", 5)
        v1 = _insert_volunteer(db, "+3333333331", "Dan")
        v2 = _insert_volunteer(db, "+3333333332", "Eve")
        _insert_signup(db, v1, sid)
        _insert_signup(db, v2, sid)

        resp = client.get("/api/coordinator/gaps?month=2026-02")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["capacity"] == 5
        assert data[0]["signup_count"] == 2
        assert data[0]["gap_size"] == 3

    def test_month_with_no_shifts_returns_empty(self, client):
        """A month with no shifts should return an empty list."""
        resp = client.get("/api/coordinator/gaps?month=2026-03")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_dropped_signups_not_counted(self, client):
        """Dropped signups should not count toward signup_count."""
        db = app.state.db
        sid = _insert_shift(db, "2026-02-20", "robe", 2)
        v1 = _insert_volunteer(db, "+4444444441", "Fay")
        v2 = _insert_volunteer(db, "+4444444442", "Gus")
        _insert_signup(db, v1, sid)
        _insert_signup(db, v2, sid)
        # Drop one signup
        db.execute(
            "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE volunteer_id = ?",
            (v2,),
        )
        db.commit()

        resp = client.get("/api/coordinator/gaps?month=2026-02")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["signup_count"] == 1
        assert data[0]["gap_size"] == 1

    def test_zero_signups_shift_appears(self, client):
        """A shift with zero signups should appear with gap_size == capacity."""
        db = app.state.db
        sid = _insert_shift(db, "2026-02-25", "kakad", 3)

        resp = client.get("/api/coordinator/gaps?month=2026-02")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["signup_count"] == 0
        assert data[0]["gap_size"] == 3
