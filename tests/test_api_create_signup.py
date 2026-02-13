"""Tests for POST /api/signups endpoint."""

from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db_connection, create_tables

# Set up in-memory test DB with cross-thread access and inject into app
import sqlite3

test_conn = sqlite3.connect(":memory:", check_same_thread=False)
test_conn.row_factory = sqlite3.Row
test_conn.execute("PRAGMA foreign_keys = ON")
create_tables(test_conn)
app.state.db = test_conn

client = TestClient(app)


def _reset_db():
    """Clear all data between tests."""
    test_conn.executescript(
        """
        DELETE FROM signups;
        DELETE FROM shifts;
        DELETE FROM volunteers;
        """
    )


def _seed_volunteer(phone: str = "1234567890", name: str = "Test Vol"):
    test_conn.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        (phone, name),
    )
    test_conn.commit()
    return test_conn.execute(
        "SELECT * FROM volunteers WHERE phone = ?", (phone,)
    ).fetchone()


def _seed_shift(
    shift_date: str = "2026-03-01",
    shift_type: str = "kakad",
    capacity: int = 2,
):
    test_conn.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (shift_date, shift_type, capacity),
    )
    test_conn.commit()
    return test_conn.execute(
        "SELECT * FROM shifts WHERE date = ? AND shift_type = ?",
        (shift_date, shift_type),
    ).fetchone()


class TestValidSignup:
    def setup_method(self):
        _reset_db()

    def test_valid_signup_returns_201(self):
        vol = _seed_volunteer()
        shift = _seed_shift()

        resp = client.post("/api/signups", json={
            "volunteer_phone": vol["phone"],
            "shift_id": shift["id"],
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["volunteer_id"] == vol["id"]
        assert data["shift_id"] == shift["id"]
        assert data["dropped_at"] is None


class TestNonexistentVolunteer:
    def setup_method(self):
        _reset_db()

    def test_unknown_phone_returns_404(self):
        shift = _seed_shift()

        resp = client.post("/api/signups", json={
            "volunteer_phone": "0000000000",
            "shift_id": shift["id"],
        })

        assert resp.status_code == 404
        assert "Volunteer not found" in resp.json()["detail"]


class TestNonexistentShift:
    def setup_method(self):
        _reset_db()

    def test_unknown_shift_returns_404(self):
        vol = _seed_volunteer()

        resp = client.post("/api/signups", json={
            "volunteer_phone": vol["phone"],
            "shift_id": 99999,
        })

        assert resp.status_code == 404
        assert "Shift not found" in resp.json()["detail"]


class TestDuplicateSignup:
    def setup_method(self):
        _reset_db()

    def test_duplicate_signup_returns_409(self):
        vol = _seed_volunteer()
        shift = _seed_shift()

        # First signup succeeds
        resp1 = client.post("/api/signups", json={
            "volunteer_phone": vol["phone"],
            "shift_id": shift["id"],
        })
        assert resp1.status_code == 201

        # Second signup is a duplicate
        resp2 = client.post("/api/signups", json={
            "volunteer_phone": vol["phone"],
            "shift_id": shift["id"],
        })
        assert resp2.status_code == 409
        assert "Duplicate" in resp2.json()["detail"]


class TestRuleViolation:
    def setup_method(self):
        _reset_db()

    def test_capacity_violation_returns_422(self):
        """When a shift is full, the signup should be rejected with 422."""
        # Create a shift with capacity 1
        shift = _seed_shift(capacity=1)

        # Fill up the shift with one volunteer
        vol1 = _seed_volunteer(phone="1111111111", name="Vol 1")
        resp1 = client.post("/api/signups", json={
            "volunteer_phone": vol1["phone"],
            "shift_id": shift["id"],
        })
        assert resp1.status_code == 201

        # Second volunteer should be rejected (capacity full)
        vol2 = _seed_volunteer(phone="2222222222", name="Vol 2")
        resp2 = client.post("/api/signups", json={
            "volunteer_phone": vol2["phone"],
            "shift_id": shift["id"],
        })
        assert resp2.status_code == 422
        detail = resp2.json()["detail"]
        assert isinstance(detail, list)
        assert len(detail) >= 1
        # Check that at least one violation has a reason string
        reasons = [v["reason"] for v in detail]
        assert any("capacity" in r.lower() or "full" in r.lower() for r in reasons)
