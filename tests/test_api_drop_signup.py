"""Tests for DELETE /api/signups/{id}."""

from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.db import get_db_connection, create_tables

# Override with in-memory test DB
import sqlite3

_raw = sqlite3.connect(":memory:", check_same_thread=False)
_raw.row_factory = sqlite3.Row
_raw.execute("PRAGMA foreign_keys = ON")
test_conn = _raw
create_tables(test_conn)
app.state.db = test_conn

client = TestClient(app)


def _ensure_db():
    """Ensure app uses our test connection."""
    app.state.db = test_conn


def _seed_signup(volunteer_id: int = 1, shift_id: int = 1) -> int:
    """Insert a volunteer, shift, and signup; return the signup id."""
    test_conn.execute(
        "INSERT OR IGNORE INTO volunteers (id, phone, name) VALUES (?, ?, ?)",
        (volunteer_id, f"+1{volunteer_id:010d}", f"Vol{volunteer_id}"),
    )
    # Use unique date per shift_id to avoid UNIQUE(date, shift_type) conflict
    test_conn.execute(
        "INSERT OR IGNORE INTO shifts (id, date, shift_type, capacity) VALUES (?, ?, ?, ?)",
        (shift_id, f"2026-02-{shift_id:02d}", "kakad", 3),
    )
    cursor = test_conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    test_conn.commit()
    return cursor.lastrowid


def test_drop_signup_valid():
    """Valid drop returns 204 and sets dropped_at."""
    _ensure_db()
    signup_id = _seed_signup(volunteer_id=10, shift_id=10)
    resp = client.delete(f"/api/signups/{signup_id}")
    assert resp.status_code == 204

    row = test_conn.execute(
        "SELECT dropped_at FROM signups WHERE id = ?", (signup_id,)
    ).fetchone()
    assert row["dropped_at"] is not None


def test_drop_signup_already_dropped():
    """Dropping an already-dropped signup returns 404."""
    _ensure_db()
    signup_id = _seed_signup(volunteer_id=20, shift_id=20)
    # Drop it once
    resp = client.delete(f"/api/signups/{signup_id}")
    assert resp.status_code == 204
    # Drop it again
    resp = client.delete(f"/api/signups/{signup_id}")
    assert resp.status_code == 404


def test_drop_signup_nonexistent():
    """Nonexistent signup_id returns 404."""
    _ensure_db()
    resp = client.delete("/api/signups/99999")
    assert resp.status_code == 404


@patch("app.routes.signups.send_message")
def test_drop_signup_triggers_notification_when_within_7_days(mock_send):
    _ensure_db()
    test_conn.execute(
        "INSERT OR IGNORE INTO volunteers (id, phone, name, is_coordinator) VALUES (?, ?, ?, ?)",
        (1, "+15104566645", "Coordinator", 1),
    )
    test_conn.execute(
        "INSERT OR IGNORE INTO volunteers (id, phone, name, is_coordinator) VALUES (?, ?, ?, ?)",
        (11, "+15104566646", "Volunteer", 0),
    )
    test_conn.execute(
        "INSERT OR IGNORE INTO shifts (id, date, shift_type, capacity) VALUES (?, date('now', '+1 day'), ?, ?)",
        (111, "kakad", 1),
    )
    signup_id = test_conn.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (11, 111),
    ).lastrowid
    test_conn.commit()

    mock_send.return_value = {"success": True, "notification_id": 1, "error": None}

    resp = client.delete(f"/api/signups/{signup_id}")
    assert resp.status_code == 204
    assert mock_send.call_count == 1
