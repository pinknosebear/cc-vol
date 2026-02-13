"""Tests for seed_volunteers()."""

from app.models.volunteer import Volunteer
from app.seed import seed_volunteers


def test_creates_10_volunteers(db):
    vols = seed_volunteers(db)
    assert len(vols) == 10


def test_idempotent(db):
    seed_volunteers(db)
    vols = seed_volunteers(db)
    assert len(vols) == 10
    # Confirm no duplicates in the table
    count = db.execute("SELECT COUNT(*) FROM volunteers").fetchone()[0]
    assert count == 10


def test_exactly_two_coordinators(db):
    vols = seed_volunteers(db)
    coordinators = [v for v in vols if v.is_coordinator]
    assert len(coordinators) == 2


def test_unique_phones(db):
    vols = seed_volunteers(db)
    phones = [v.phone for v in vols]
    assert len(set(phones)) == 10


def test_returns_volunteer_objects(db):
    vols = seed_volunteers(db)
    for v in vols:
        assert isinstance(v, Volunteer)
