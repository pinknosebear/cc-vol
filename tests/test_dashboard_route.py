import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_returns_200(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_contains_key_elements(client):
    resp = client.get("/dashboard")
    html = resp.text
    assert "month-picker" in html
    assert "calendar" in html
    assert "day-detail" in html
    assert "gaps" in html
    assert "volunteers" in html
    assert "main.js" in html
