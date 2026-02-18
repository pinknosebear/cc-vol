"""Tests for volunteer removal (DELETE /api/volunteers/{phone})."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.volunteer import (
    VolunteerCreate,
    create_volunteer,
    get_volunteer_by_phone,
    list_volunteers,
    remove_volunteer,
)


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

def test_remove_volunteer_sets_removed_at(db):
    """remove_volunteer sets removed_at on the record."""
    create_volunteer(db, VolunteerCreate(phone="+1000000001", name="Alice"))
    vol = remove_volunteer(db, "+1000000001")
    assert vol is not None
    assert vol.removed_at is not None


def test_remove_volunteer_not_found_returns_none(db):
    """remove_volunteer returns None for unknown phone."""
    result = remove_volunteer(db, "+0000000000")
    assert result is None


def test_remove_volunteer_already_removed_returns_none(db):
    """Calling remove_volunteer twice returns None on the second call."""
    create_volunteer(db, VolunteerCreate(phone="+1000000002", name="Bob"))
    remove_volunteer(db, "+1000000002")
    result = remove_volunteer(db, "+1000000002")
    assert result is None


def test_removed_volunteer_excluded_from_list(db):
    """list_volunteers does not return removed volunteers."""
    create_volunteer(db, VolunteerCreate(phone="+1000000003", name="Carol"))
    create_volunteer(db, VolunteerCreate(phone="+1000000004", name="Dave"))
    remove_volunteer(db, "+1000000003")

    vols = list_volunteers(db)
    phones = {v.phone for v in vols}
    assert "+1000000003" not in phones
    assert "+1000000004" in phones


def test_removed_volunteer_not_found_by_phone(db):
    """get_volunteer_by_phone returns None for a removed volunteer."""
    create_volunteer(db, VolunteerCreate(phone="+1000000005", name="Eve"))
    remove_volunteer(db, "+1000000005")
    result = get_volunteer_by_phone(db, "+1000000005")
    assert result is None


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db):
    app.state.db = db
    return TestClient(app)


def test_delete_volunteer_returns_204(client, db):
    """DELETE /api/volunteers/{phone} returns 204 on success."""
    create_volunteer(db, VolunteerCreate(phone="+2000000001", name="Frank"))
    resp = client.delete("/api/volunteers/%2B2000000001")
    assert resp.status_code == 204


def test_delete_volunteer_not_found_returns_404(client):
    """DELETE /api/volunteers/{phone} returns 404 for unknown volunteer."""
    resp = client.delete("/api/volunteers/%2B9999999999")
    assert resp.status_code == 404


def test_delete_volunteer_already_removed_returns_404(client, db):
    """Removing an already-removed volunteer returns 404."""
    create_volunteer(db, VolunteerCreate(phone="+2000000002", name="Grace"))
    client.delete("/api/volunteers/%2B2000000002")
    resp = client.delete("/api/volunteers/%2B2000000002")
    assert resp.status_code == 404


def test_deleted_volunteer_absent_from_list(client, db):
    """Removed volunteer does not appear in GET /api/volunteers."""
    create_volunteer(db, VolunteerCreate(phone="+2000000003", name="Hank"))
    client.delete("/api/volunteers/%2B2000000003")

    resp = client.get("/api/volunteers")
    assert resp.status_code == 200
    phones = [v["phone"] for v in resp.json()]
    assert "+2000000003" not in phones
