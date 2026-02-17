"""Verify gaps API response has required fields for gaps renderer."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed import seed_month


@pytest.fixture
def client(db):
    app.state.db = db
    seed_month(db, 2026, 3)
    return TestClient(app)


def test_gaps_returns_list(client):
    resp = client.get("/api/coordinator/gaps?month=2026-03")
    assert resp.status_code == 200
    gaps = resp.json()
    assert isinstance(gaps, list)
    # With no signups, all shifts should be gaps
    assert len(gaps) == 62  # 31 days * 2 types


def test_gaps_have_required_fields(client):
    resp = client.get("/api/coordinator/gaps?month=2026-03")
    gaps = resp.json()
    for gap in gaps[:5]:  # Check first few
        assert "date" in gap
        assert "type" in gap
        assert "capacity" in gap
        assert "signup_count" in gap


def test_gaps_have_correct_capacity_values(client):
    resp = client.get("/api/coordinator/gaps?month=2026-03")
    gaps = resp.json()
    kakad_gaps = [g for g in gaps if g["type"] == "kakad"]
    for g in kakad_gaps:
        assert g["capacity"] == 1
