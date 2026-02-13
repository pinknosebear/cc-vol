"""Tests for GET /api/volunteers/{phone}/shifts."""

import sqlite3
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.db import create_tables
from app.models.volunteer import VolunteerCreate, create_volunteer
from app.models.shift import ShiftCreate, create_shift
from app.models.signup import SignupCreate, create_signup, drop_signup

# ---------------------------------------------------------------------------
# Fresh in-memory DB for each module import (isolated from other test files)
# check_same_thread=False required because FastAPI runs handlers in a thread pool
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_valid_phone_returns_shifts():
    """A volunteer with active signups gets back shift details."""
    _reset_db()
    vol = create_volunteer(test_conn, VolunteerCreate(phone="1111111111", name="Sonia"))
    s1 = create_shift(test_conn, ShiftCreate(date=date(2026, 2, 3), type="kakad", capacity=1))
    s2 = create_shift(test_conn, ShiftCreate(date=date(2026, 2, 5), type="robe", capacity=3))
    create_signup(test_conn, SignupCreate(volunteer_id=vol.id, shift_id=s1.id))
    create_signup(test_conn, SignupCreate(volunteer_id=vol.id, shift_id=s2.id))

    resp = client.get("/api/volunteers/1111111111/shifts?month=2026-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["shift_id"] == s1.id
    assert data[0]["date"] == "2026-02-03"
    assert data[0]["type"] == "kakad"
    assert data[1]["shift_id"] == s2.id
    assert data[1]["date"] == "2026-02-05"
    assert data[1]["type"] == "robe"


def test_no_shifts_returns_empty():
    """A volunteer with no signups gets an empty list."""
    _reset_db()
    create_volunteer(test_conn, VolunteerCreate(phone="2222222222", name="Raghu"))

    resp = client.get("/api/volunteers/2222222222/shifts?month=2026-02")
    assert resp.status_code == 200
    assert resp.json() == []


def test_dropped_shifts_excluded():
    """Dropped signups should not appear in the response."""
    _reset_db()
    vol = create_volunteer(test_conn, VolunteerCreate(phone="3333333333", name="Ganesh"))
    s1 = create_shift(test_conn, ShiftCreate(date=date(2026, 2, 10), type="kakad", capacity=1))
    s2 = create_shift(test_conn, ShiftCreate(date=date(2026, 2, 11), type="robe", capacity=3))
    create_signup(test_conn, SignupCreate(volunteer_id=vol.id, shift_id=s1.id))
    su2 = create_signup(test_conn, SignupCreate(volunteer_id=vol.id, shift_id=s2.id))
    drop_signup(test_conn, su2.id)

    resp = client.get("/api/volunteers/3333333333/shifts?month=2026-02")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["shift_id"] == s1.id


def test_unknown_phone_returns_404():
    """An unregistered phone number returns 404."""
    _reset_db()
    resp = client.get("/api/volunteers/0000000000/shifts?month=2026-02")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Volunteer not found"
