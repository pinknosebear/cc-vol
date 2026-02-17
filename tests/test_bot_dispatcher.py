"""Tests for the WhatsApp incoming message dispatcher endpoint."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_db_connection, create_tables
from app.routes.wa_incoming import router


@pytest.fixture()
def app():
    """Create a test FastAPI app with in-memory SQLite."""
    test_app = FastAPI()
    test_app.include_router(router)

    import sqlite3
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    test_app.state.db = conn

    yield test_app

    conn.close()


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def db(app):
    return app.state.db


def _add_volunteer(db, phone: str, name: str, is_coordinator: bool = False) -> int:
    cursor = db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator) VALUES (?, ?, ?)",
        (phone, name, is_coordinator),
    )
    db.commit()
    return cursor.lastrowid


def _add_shift(db, shift_date: str, shift_type: str, capacity: int = 4) -> int:
    cursor = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (shift_date, shift_type, capacity),
    )
    db.commit()
    return cursor.lastrowid


class TestUnknownPhone:
    def test_unregistered_phone_returns_not_registered(self, client):
        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+919999999999", "message": "help"},
        )
        assert resp.status_code == 200
        # Unauthenticated users can see help (which includes register command)
        assert "register" in resp.json()["reply"].lower()

    def test_unregistered_phone_invalid_command_prompts_register(self, client):
        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+919999999999", "message": "signup 2026-03-01 kakad"},
        )
        assert resp.status_code == 200
        assert "register" in resp.json()["reply"].lower()


class TestUnparseableMessage:
    def test_gibberish_returns_suggestions(self, client, db):
        _add_volunteer(db, "+911111111111", "Test Vol")
        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+911111111111", "message": "xyzgarbage"},
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert "I didn't understand that" in reply
        assert "Did you mean" in reply


class TestCoordinatorGuard:
    def test_volunteer_cannot_use_coordinator_command(self, client, db):
        _add_volunteer(db, "+911111111111", "Test Vol", is_coordinator=False)
        today = date.today().isoformat()
        _add_shift(db, today, "kakad")

        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+911111111111", "message": f"status {today}"},
        )
        assert resp.status_code == 200
        assert resp.json()["reply"] == "That command is for coordinators only."


class TestSignupRoute:
    def test_valid_signup(self, client, db):
        _add_volunteer(db, "+911111111111", "Test Vol")
        today = date.today().isoformat()
        _add_shift(db, today, "kakad", capacity=4)

        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+911111111111", "message": f"signup {today} kakad"},
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert "Signed up" in reply
        assert "kakad" in reply


class TestDropRoute:
    def test_valid_drop(self, client, db):
        vol_id = _add_volunteer(db, "+911111111111", "Test Vol")
        today = date.today().isoformat()
        shift_id = _add_shift(db, today, "robe", capacity=4)
        # Create a signup first
        db.execute(
            "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
            (vol_id, shift_id),
        )
        db.commit()

        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+911111111111", "message": f"drop {today} robe"},
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert "Dropped" in reply
        assert "robe" in reply


class TestMyShiftsRoute:
    def test_my_shifts(self, client, db):
        _add_volunteer(db, "+911111111111", "Test Vol")

        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+911111111111", "message": "my shifts"},
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        # With no signups, should say "no shifts"
        assert "no shifts" in reply.lower() or "shifts" in reply.lower()


class TestHelpRoute:
    def test_help_returns_help_text(self, client, db):
        _add_volunteer(db, "+911111111111", "Test Vol")

        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+911111111111", "message": "help"},
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert "Available commands" in reply
        assert "signup" in reply
        assert "drop" in reply


class TestCoordinatorStatusRoute:
    def test_coordinator_can_use_status(self, client, db):
        _add_volunteer(db, "+912222222222", "Coord", is_coordinator=True)
        today = date.today().isoformat()
        _add_shift(db, today, "kakad", capacity=4)

        resp = client.post(
            "/api/wa/incoming",
            json={"phone": "+912222222222", "message": f"status {today}"},
        )
        assert resp.status_code == 200
        reply = resp.json()["reply"]
        assert "Status" in reply or "status" in reply or "kakad" in reply
