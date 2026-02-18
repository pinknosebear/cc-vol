import sqlite3

import pytest

from app.models.volunteer import (
    Volunteer,
    VolunteerCreate,
    create_volunteer,
    get_volunteer_by_phone,
    list_volunteers,
    normalize_phone,
)


def test_create_volunteer(db):
    data = VolunteerCreate(phone="+1234567890", name="Alice")
    vol = create_volunteer(db, data)

    assert vol.id is not None
    assert vol.phone == "+1234567890"
    assert vol.name == "Alice"
    assert vol.is_coordinator is False
    assert vol.created_at is not None


def test_create_volunteer_normalizes_10_digit(db):
    data = VolunteerCreate(phone="5104566645", name="Alice")
    vol = create_volunteer(db, data)
    assert vol.phone == "+15104566645"


def test_get_volunteer_by_phone(db):
    data = VolunteerCreate(phone="+1111111111", name="Bob")
    create_volunteer(db, data)

    found = get_volunteer_by_phone(db, "+1111111111")
    assert found is not None
    assert found.name == "Bob"
    assert found.phone == "+1111111111"


def test_get_volunteer_by_phone_matches_legacy_plain(db):
    db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator, status) VALUES (?, ?, ?, ?)",
        ("5104566645", "Legacy Bob", False, "approved"),
    )
    db.commit()

    found = get_volunteer_by_phone(db, "+15104566645")
    assert found is not None
    assert found.name == "Legacy Bob"
    assert found.phone == "5104566645"


def test_normalize_phone_with_default_area_code(monkeypatch):
    monkeypatch.setenv("DEFAULT_AREA_CODE", "510")
    assert normalize_phone("4566645") == "+15104566645"


def test_get_volunteer_by_phone_not_found(db):
    result = get_volunteer_by_phone(db, "+0000000000")
    assert result is None


def test_list_volunteers(db):
    create_volunteer(db, VolunteerCreate(phone="+1111", name="A"))
    create_volunteer(db, VolunteerCreate(phone="+2222", name="B"))
    create_volunteer(db, VolunteerCreate(phone="+3333", name="C"))

    vols = list_volunteers(db)
    assert len(vols) == 3
    names = {v.name for v in vols}
    assert names == {"A", "B", "C"}


def test_duplicate_phone_raises(db):
    create_volunteer(db, VolunteerCreate(phone="+9999", name="First"))
    with pytest.raises(sqlite3.IntegrityError):
        create_volunteer(db, VolunteerCreate(phone="+9999", name="Second"))


def test_is_coordinator_defaults_false(db):
    vol = create_volunteer(db, VolunteerCreate(phone="+5555", name="Default"))
    assert vol.is_coordinator is False


def test_create_coordinator(db):
    vol = create_volunteer(
        db, VolunteerCreate(phone="+7777", name="Coord", is_coordinator=True)
    )
    assert vol.is_coordinator is True
