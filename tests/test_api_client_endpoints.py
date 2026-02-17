"""Verify API response shapes match what the JS client expects."""
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


def test_shifts_month_returns_list_with_required_fields(client):
    resp = client.get("/api/shifts?month=2026-03")
    assert resp.status_code == 200
    shifts = resp.json()
    assert isinstance(shifts, list)
    assert len(shifts) > 0
    shift = shifts[0]
    for field in ("id", "date", "type", "capacity", "signup_count"):
        assert field in shift, f"Missing field: {field}"


def test_day_detail_returns_shifts_with_volunteers(client):
    resp = client.get("/api/shifts/2026-03-15")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        shift = data[0]
        assert "type" in shift
        assert "capacity" in shift


def test_gaps_returns_list_with_gap_size(client):
    resp = client.get("/api/coordinator/gaps?month=2026-03")
    assert resp.status_code == 200
    gaps = resp.json()
    assert isinstance(gaps, list)
    if len(gaps) > 0:
        gap = gaps[0]
        for field in ("date", "type", "capacity", "signup_count"):
            assert field in gap


def test_volunteers_returns_list(client):
    resp = client.get("/api/volunteers")
    assert resp.status_code == 200
    vols = resp.json()
    assert isinstance(vols, list)
    assert len(vols) > 0


def test_seed_endpoint_creates_shifts(client):
    resp = client.post("/api/coordinator/seed/2026/4")
    assert resp.status_code == 200
