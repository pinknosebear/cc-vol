"""Tests for GET /api/shifts?month=YYYY-MM."""

from fastapi.testclient import TestClient

from app.main import app
import sqlite3
from app.db import create_tables

# Set up in-memory test DB (check_same_thread=False needed for TestClient's thread)
test_conn = sqlite3.connect(":memory:", check_same_thread=False)
test_conn.row_factory = sqlite3.Row
test_conn.execute("PRAGMA foreign_keys = ON")
create_tables(test_conn)
app.state.db = test_conn

client = TestClient(app)


def _reset_db():
    """Clear all data between tests."""
    app.state.db = test_conn
    test_conn.execute("DELETE FROM signups")
    test_conn.execute("DELETE FROM shifts")
    test_conn.execute("DELETE FROM volunteers")
    test_conn.commit()


def _seed_volunteer(phone: str = "+1111111111", name: str = "Test Vol") -> int:
    cursor = test_conn.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)", (phone, name)
    )
    test_conn.commit()
    return cursor.lastrowid


def _seed_shift(date: str, shift_type: str, capacity: int) -> int:
    cursor = test_conn.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (date, shift_type, capacity),
    )
    test_conn.commit()
    return cursor.lastrowid


def _seed_signup(volunteer_id: int, shift_id: int, dropped: bool = False):
    cursor = test_conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    if dropped:
        test_conn.execute(
            "UPDATE signups SET dropped_at = CURRENT_TIMESTAMP WHERE id = ?",
            (cursor.lastrowid,),
        )
    test_conn.commit()


def test_valid_month_returns_shifts_with_counts():
    _reset_db()
    vol_id = _seed_volunteer()
    s1 = _seed_shift("2026-03-01", "kakad", 2)
    s2 = _seed_shift("2026-03-01", "robe", 3)
    s3 = _seed_shift("2026-03-15", "kakad", 2)

    # Active signup on s1
    _seed_signup(vol_id, s1)
    # Dropped signup on s2 — should NOT count
    _seed_signup(vol_id, s2, dropped=True)

    resp = client.get("/api/shifts", params={"month": "2026-03"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3

    # Shifts are ordered by date, then shift_type
    assert data[0]["id"] == s1
    assert data[0]["date"] == "2026-03-01"
    assert data[0]["type"] == "kakad"
    assert data[0]["capacity"] == 2
    assert data[0]["signup_count"] == 1

    assert data[1]["id"] == s2
    assert data[1]["type"] == "robe"
    assert data[1]["signup_count"] == 0  # dropped signup doesn't count

    assert data[2]["id"] == s3
    assert data[2]["signup_count"] == 0


def test_invalid_month_format_returns_error():
    resp = client.get("/api/shifts", params={"month": "bad"})
    assert resp.status_code == 400

    resp = client.get("/api/shifts", params={"month": "2026-13"})
    assert resp.status_code == 400

    resp = client.get("/api/shifts", params={"month": "2026-00"})
    assert resp.status_code == 400


def test_missing_month_param_returns_422():
    resp = client.get("/api/shifts")
    assert resp.status_code == 422


def test_month_with_no_shifts_returns_empty():
    _reset_db()
    resp = client.get("/api/shifts", params={"month": "2099-01"})
    assert resp.status_code == 200
    assert resp.json() == []
