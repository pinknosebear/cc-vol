"""Verify shift data structure has all fields needed by calendar renderer."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed import seed_month


@pytest.fixture
def client(db):
    app.state.db = db
    seed_month(db, 2026, 3)
    return TestClient(app)


def test_shifts_contain_required_calendar_fields(client):
    resp = client.get("/api/shifts?month=2026-03")
    assert resp.status_code == 200
    shifts = resp.json()
    assert len(shifts) == 62  # 31 days * 2 types
    for shift in shifts:
        assert "id" in shift
        assert "date" in shift
        assert "type" in shift
        assert "capacity" in shift
        assert "signup_count" in shift


def test_shifts_have_correct_types(client):
    resp = client.get("/api/shifts?month=2026-03")
    shifts = resp.json()
    types = {s["type"] for s in shifts}
    assert types == {"kakad", "robe"}
