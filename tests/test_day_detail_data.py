"""Verify day detail and available volunteers API response shapes."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed import seed_month, seed_volunteers


@pytest.fixture
def client(db):
    app.state.db = db
    seed_month(db, 2026, 3)
    seed_volunteers(db)
    return TestClient(app)


def test_day_detail_returns_list_of_shifts(client):
    resp = client.get("/api/shifts/2026-03-15")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2  # kakad + robe


def test_day_detail_shift_has_type_and_capacity(client):
    resp = client.get("/api/shifts/2026-03-15")
    data = resp.json()
    for shift in data:
        assert "type" in shift
        assert "capacity" in shift
        assert "volunteers" in shift
        assert isinstance(shift["volunteers"], list)


def test_available_volunteers_returns_list(client):
    resp = client.get("/api/coordinator/volunteers/available?date=2026-03-15")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
