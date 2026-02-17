import os
import pytest

# Set env var before importing app
os.environ["DB_PATH"] = "/tmp/test-deploy-cc-vol.db"

from fastapi.testclient import TestClient
from app.main import app


def test_healthz_with_custom_db_path():
    """Test that FastAPI starts correctly with a custom DB_PATH environment variable."""
    # Clean up any existing test database
    if os.path.exists("/tmp/test-deploy-cc-vol.db"):
        os.remove("/tmp/test-deploy-cc-vol.db")
    
    # Use context manager to ensure startup/shutdown events are triggered
    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Verify the database file was created at the custom path
        assert os.path.exists("/tmp/test-deploy-cc-vol.db"), "Database file not created at custom path"


def test_cleanup():
    """Clean up the test database file."""
    if os.path.exists("/tmp/test-deploy-cc-vol.db"):
        os.remove("/tmp/test-deploy-cc-vol.db")
