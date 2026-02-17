"""Verify volunteer and seed API response shapes for dashboard."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed import seed_volunteers


@pytest.fixture
def client(db):
    app.state.db = db
    seed_volunteers(db)
    return TestClient(app)


def test_get_volunteers_returns_list(client):
    resp = client.get("/api/volunteers")
    assert resp.status_code == 200
    vols = resp.json()
    assert isinstance(vols, list)
    assert len(vols) >= 10  # seed creates 10


def test_volunteer_has_required_fields(client):
    resp = client.get("/api/volunteers")
    vols = resp.json()
    vol = vols[0]
    assert "name" in vol
    assert "phone" in vol
    assert "is_coordinator" in vol


def test_create_volunteer(client):
    resp = client.post("/api/volunteers", json={
        "phone": "5550001111",
        "name": "Test User",
        "is_coordinator": False,
    })
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["name"] == "Test User"


def test_seed_month_endpoint(client):
    resp = client.post("/api/coordinator/seed/2026/4")
    assert resp.status_code == 200
