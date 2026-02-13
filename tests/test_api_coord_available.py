"""Tests for GET /api/coordinator/volunteers/available."""

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db_connection, create_tables

# ---------------------------------------------------------------------------
# Test DB setup
# ---------------------------------------------------------------------------

import sqlite3 as _sqlite3

_raw_conn = _sqlite3.connect(":memory:", check_same_thread=False)
_raw_conn.row_factory = _sqlite3.Row
_raw_conn.execute("PRAGMA foreign_keys = ON")
create_tables(_raw_conn)
test_conn = _raw_conn
app.state.db = test_conn

client = TestClient(app)


def _reset_db():
    """Clear all data between tests."""
    app.state.db = test_conn
    test_conn.execute("DELETE FROM signups")
    test_conn.execute("DELETE FROM shifts")
    test_conn.execute("DELETE FROM volunteers")
    test_conn.commit()


def _add_volunteer(phone: str, name: str) -> int:
    cursor = test_conn.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)", (phone, name)
    )
    test_conn.commit()
    return cursor.lastrowid


def _add_shift(date_str: str, shift_type: str = "kakad", capacity: int = 3) -> int:
    cursor = test_conn.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (date_str, shift_type, capacity),
    )
    test_conn.commit()
    return cursor.lastrowid


def _add_signup(volunteer_id: int, shift_id: int):
    test_conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    test_conn.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_volunteers_under_limit():
    """Volunteers with fewer than 8 signups should appear in the response."""
    _reset_db()
    vid = _add_volunteer("+1111", "Alice")

    # Give Alice 3 signups in Feb 2026
    for day in range(1, 4):
        sid = _add_shift(f"2026-02-{day:02d}", "kakad")
        _add_signup(vid, sid)

    resp = client.get("/api/coordinator/volunteers/available?date=2026-02-15")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == vid
    assert data[0]["name"] == "Alice"
    assert data[0]["phone"] == "+1111"
    assert data[0]["total_signups"] == 3
    assert data[0]["remaining_slots"] == 5


def test_excludes_volunteers_at_limit():
    """Volunteers with 8 or more signups should NOT appear."""
    _reset_db()
    vid_full = _add_volunteer("+2222", "Bob")
    vid_free = _add_volunteer("+3333", "Carol")

    # Bob gets 8 signups (at limit)
    for day in range(1, 9):
        sid = _add_shift(f"2026-02-{day:02d}", "kakad" if day % 2 == 0 else "robe")
        _add_signup(vid_full, sid)

    # Carol gets 2 signups (under limit)
    for day in range(10, 12):
        sid = _add_shift(f"2026-02-{day:02d}", "kakad")
        _add_signup(vid_free, sid)

    resp = client.get("/api/coordinator/volunteers/available?date=2026-02-15")
    assert resp.status_code == 200
    data = resp.json()

    ids = [v["id"] for v in data]
    assert vid_full not in ids
    assert vid_free in ids

    carol = next(v for v in data if v["id"] == vid_free)
    assert carol["total_signups"] == 2
    assert carol["remaining_slots"] == 6


def test_excludes_volunteers_over_limit():
    """Volunteers with more than 8 signups should NOT appear."""
    _reset_db()
    vid = _add_volunteer("+4444", "Dave")

    # 9 signups (over limit)
    for day in range(1, 10):
        sid = _add_shift(f"2026-02-{day:02d}", "kakad" if day % 2 == 0 else "robe")
        _add_signup(vid, sid)

    resp = client.get("/api/coordinator/volunteers/available?date=2026-02-15")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_invalid_date_returns_422():
    """Non-date string should return 422."""
    _reset_db()
    resp = client.get("/api/coordinator/volunteers/available?date=not-a-date")
    assert resp.status_code == 422


def test_missing_date_returns_422():
    """Missing date query param should return 422."""
    _reset_db()
    resp = client.get("/api/coordinator/volunteers/available")
    assert resp.status_code == 422


def test_different_month_not_counted():
    """Signups in a different month should not affect availability."""
    _reset_db()
    vid = _add_volunteer("+5555", "Eve")

    # 8 signups in January
    for day in range(1, 9):
        sid = _add_shift(f"2026-01-{day:02d}", "kakad" if day % 2 == 0 else "robe")
        _add_signup(vid, sid)

    # Query for February -- Eve should be available with 0 signups
    resp = client.get("/api/coordinator/volunteers/available?date=2026-02-15")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["total_signups"] == 0
    assert data[0]["remaining_slots"] == 8
