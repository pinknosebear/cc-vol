from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db_connection, create_tables

# Override with in-memory test DB
test_conn = get_db_connection(":memory:")
create_tables(test_conn)
app.state.db = test_conn

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_404():
    response = client.get("/nonexistent")
    assert response.status_code == 404
