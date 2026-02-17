"""End-to-end smoke test for coordinator dashboard API contract."""

import pytest
from fastapi.testclient import TestClient

from app.db import create_tables
from app.main import app


@pytest.fixture
def client(db):
    app.state.db = db
    return TestClient(app)


def test_full_dashboard_flow(client):
    """Simulate the full dashboard lifecycle via API."""

    # 1. Seed March 2026 shifts
    resp = client.post("/api/coordinator/seed/2026/3")
    assert resp.status_code == 200, f"Seed failed: {resp.text}"

    # 2. Create a test volunteer
    resp = client.post("/api/volunteers", json={
        "phone": "1234567890",
        "name": "E2E Test User",
        "is_coordinator": False,
    })
    assert resp.status_code in (200, 201), f"Create volunteer failed: {resp.text}"

    # 3. GET /api/shifts?month=2026-03 — verify shifts exist
    resp = client.get("/api/shifts?month=2026-03")
    assert resp.status_code == 200
    shifts = resp.json()
    assert len(shifts) == 62, f"Expected 62 shifts (31 days x 2), got {len(shifts)}"

    # Verify shift structure
    shift = shifts[0]
    assert "id" in shift
    assert "date" in shift
    assert "type" in shift
    assert "capacity" in shift
    assert "signup_count" in shift

    # 4. GET /api/shifts/2026-03-15 — day detail
    resp = client.get("/api/shifts/2026-03-15")
    assert resp.status_code == 200
    day = resp.json()
    assert isinstance(day, list)
    assert len(day) == 2  # kakad + robe
    types = {s["type"] for s in day}
    assert types == {"kakad", "robe"}

    # 5. GET /api/coordinator/gaps?month=2026-03 — all shifts are gaps (no signups)
    resp = client.get("/api/coordinator/gaps?month=2026-03")
    assert resp.status_code == 200
    gaps = resp.json()
    assert len(gaps) == 62, f"Expected 62 gaps (no signups yet), got {len(gaps)}"

    # 6. GET /api/coordinator/volunteers/available?date=2026-03-15
    resp = client.get("/api/coordinator/volunteers/available?date=2026-03-15")
    assert resp.status_code == 200
    available = resp.json()
    assert isinstance(available, list)
    # Our test volunteer should be available (no signups)
    names = [v["name"] for v in available]
    assert "E2E Test User" in names

    # 7. GET /dashboard — verify HTML loads
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text
    assert "month-picker" in html
    assert "calendar" in html
    assert "main.js" in html


def test_seed_idempotent(client):
    """Seeding twice should not create duplicate shifts."""
    client.post("/api/coordinator/seed/2026/3")
    client.post("/api/coordinator/seed/2026/3")
    resp = client.get("/api/shifts?month=2026-03")
    assert len(resp.json()) == 62


def test_empty_month_no_error(client):
    """Querying an unseeded month should return empty, not error."""
    resp = client.get("/api/shifts?month=2025-01")
    assert resp.status_code == 200
    assert resp.json() == []
