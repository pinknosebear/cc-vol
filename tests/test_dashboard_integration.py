"""Integration test: dashboard HTML includes all required script tags and container divs."""
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


def test_dashboard_returns_html(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_has_all_container_divs(client):
    html = client.get("/dashboard").text
    for div_id in ["month-picker", "calendar", "day-detail", "gaps", "volunteers"]:
        assert f'id="{div_id}"' in html, f"Missing container div #{div_id}"


def test_dashboard_has_all_script_tags(client):
    html = client.get("/dashboard").text
    for module in ["api.js", "month-picker.js", "calendar.js", "day-detail.js", "gaps.js", "volunteers.js", "main.js"]:
        assert module in html, f"Missing script tag for {module}"


def test_dashboard_has_tab_buttons(client):
    html = client.get("/dashboard").text
    assert "data-tab" in html
    for tab in ["calendar", "gaps", "volunteers"]:
        assert f'data-tab="{tab}"' in html, f"Missing tab button for {tab}"


def test_api_shifts_works_for_dashboard(client):
    resp = client.get("/api/shifts?month=2026-03")
    assert resp.status_code == 200
    shifts = resp.json()
    assert len(shifts) == 62


def test_api_gaps_works_for_dashboard(client):
    resp = client.get("/api/coordinator/gaps?month=2026-03")
    assert resp.status_code == 200


def test_api_volunteers_works_for_dashboard(client):
    resp = client.get("/api/volunteers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 10
