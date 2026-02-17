"""Tests for volunteer status lifecycle (pending/approved/rejected)."""

import sqlite3
import pytest

from app.models.volunteer import (
    Volunteer,
    VolunteerCreate,
    create_volunteer,
    get_volunteer_by_phone,
    list_volunteers,
    get_pending_volunteers,
    approve_volunteer,
    reject_volunteer,
)


def test_create_pending_volunteer(db):
    """Test creating a volunteer with status='pending'."""
    data = VolunteerCreate(phone="+1234567890", name="Alice", status="pending")
    vol = create_volunteer(db, data)

    assert vol.id is not None
    assert vol.phone == "+1234567890"
    assert vol.name == "Alice"
    assert vol.status == "pending"
    assert vol.requested_at is None
    assert vol.approved_at is None
    assert vol.approved_by is None


def test_create_approved_volunteer_default(db):
    """Test that default status is 'approved'."""
    data = VolunteerCreate(phone="+1111111111", name="Bob")
    vol = create_volunteer(db, data)

    assert vol.status == "approved"


def test_create_approved_volunteer_explicit(db):
    """Test creating a volunteer with explicit status='approved'."""
    data = VolunteerCreate(phone="+2222222222", name="Charlie", status="approved")
    vol = create_volunteer(db, data)

    assert vol.status == "approved"
    assert vol.approved_at is None  # No timestamp yet
    assert vol.approved_by is None


def test_list_volunteers_all(db):
    """Test listing all volunteers regardless of status."""
    create_volunteer(db, VolunteerCreate(phone="+1111", name="A", status="pending"))
    create_volunteer(db, VolunteerCreate(phone="+2222", name="B", status="approved"))
    create_volunteer(db, VolunteerCreate(phone="+3333", name="C", status="pending"))

    vols = list_volunteers(db)
    assert len(vols) == 3


def test_list_volunteers_by_status_pending(db):
    """Test listing only pending volunteers."""
    create_volunteer(db, VolunteerCreate(phone="+1111", name="A", status="pending"))
    create_volunteer(db, VolunteerCreate(phone="+2222", name="B", status="approved"))
    create_volunteer(db, VolunteerCreate(phone="+3333", name="C", status="pending"))

    pending = list_volunteers(db, status="pending")
    assert len(pending) == 2
    names = {v.name for v in pending}
    assert names == {"A", "C"}


def test_list_volunteers_by_status_approved(db):
    """Test listing only approved volunteers."""
    create_volunteer(db, VolunteerCreate(phone="+1111", name="A", status="pending"))
    create_volunteer(db, VolunteerCreate(phone="+2222", name="B", status="approved"))
    create_volunteer(db, VolunteerCreate(phone="+3333", name="C", status="approved"))

    approved = list_volunteers(db, status="approved")
    assert len(approved) == 2
    names = {v.name for v in approved}
    assert names == {"B", "C"}


def test_list_volunteers_by_status_rejected(db):
    """Test listing only rejected volunteers."""
    create_volunteer(db, VolunteerCreate(phone="+1111", name="A", status="pending"))
    create_volunteer(db, VolunteerCreate(phone="+2222", name="B", status="rejected"))
    create_volunteer(db, VolunteerCreate(phone="+3333", name="C", status="rejected"))

    rejected = list_volunteers(db, status="rejected")
    assert len(rejected) == 2
    names = {v.name for v in rejected}
    assert names == {"B", "C"}


def test_get_pending_volunteers(db):
    """Test the get_pending_volunteers helper function."""
    create_volunteer(db, VolunteerCreate(phone="+1111", name="A", status="pending"))
    create_volunteer(db, VolunteerCreate(phone="+2222", name="B", status="approved"))
    create_volunteer(db, VolunteerCreate(phone="+3333", name="C", status="pending"))

    pending = get_pending_volunteers(db)
    assert len(pending) == 2
    names = {v.name for v in pending}
    assert names == {"A", "C"}


def test_approve_volunteer(db):
    """Test approving a pending volunteer."""
    # Create a pending volunteer
    pending_vol = create_volunteer(
        db, VolunteerCreate(phone="+1111", name="Alice", status="pending")
    )

    # Create an approver (a coordinator)
    approver = create_volunteer(
        db, VolunteerCreate(phone="+9999", name="Coordinator", is_coordinator=True)
    )

    # Approve the pending volunteer
    approved_vol = approve_volunteer(db, "+1111", approver.id)

    assert approved_vol is not None
    assert approved_vol.phone == "+1111"
    assert approved_vol.status == "approved"
    assert approved_vol.approved_at is not None
    assert approved_vol.approved_by == approver.id

    # Verify in database
    vol_from_db = get_volunteer_by_phone(db, "+1111")
    assert vol_from_db.status == "approved"
    assert vol_from_db.approved_by == approver.id


def test_approve_nonexistent_volunteer(db):
    """Test that approving a non-existent volunteer returns None."""
    approver = create_volunteer(
        db, VolunteerCreate(phone="+9999", name="Coordinator", is_coordinator=True)
    )

    result = approve_volunteer(db, "+0000000000", approver.id)
    assert result is None


def test_reject_volunteer(db):
    """Test rejecting a pending volunteer."""
    # Create a pending volunteer
    pending_vol = create_volunteer(
        db, VolunteerCreate(phone="+1111", name="Alice", status="pending")
    )

    # Reject the volunteer
    rejected_vol = reject_volunteer(db, "+1111")

    assert rejected_vol is not None
    assert rejected_vol.phone == "+1111"
    assert rejected_vol.status == "rejected"

    # Verify in database
    vol_from_db = get_volunteer_by_phone(db, "+1111")
    assert vol_from_db.status == "rejected"


def test_reject_nonexistent_volunteer(db):
    """Test that rejecting a non-existent volunteer returns None."""
    result = reject_volunteer(db, "+0000000000")
    assert result is None


def test_status_enum_constraint(db):
    """Test that invalid status values are rejected."""
    # Try to insert an invalid status directly (should fail)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO volunteers (phone, name, status) VALUES (?, ?, ?)",
            ("+9999", "Invalid", "invalid_status"),
        )
        db.commit()


def test_approve_volunteer_with_timestamp(db):
    """Test that approve_volunteer sets approved_at timestamp."""
    pending_vol = create_volunteer(
        db, VolunteerCreate(phone="+1111", name="Alice", status="pending")
    )
    approver = create_volunteer(
        db, VolunteerCreate(phone="+9999", name="Coordinator", is_coordinator=True)
    )

    approved_vol = approve_volunteer(db, "+1111", approver.id)

    # Check that approved_at is set
    assert approved_vol.approved_at is not None
    assert approved_vol.requested_at is None  # requested_at not set by default


def test_multiple_approvals_in_sequence(db):
    """Test creating and approving multiple pending volunteers."""
    # Create pending volunteers
    vol1 = create_volunteer(
        db, VolunteerCreate(phone="+1111", name="Alice", status="pending")
    )
    vol2 = create_volunteer(
        db, VolunteerCreate(phone="+2222", name="Bob", status="pending")
    )

    # Create approver
    approver = create_volunteer(
        db, VolunteerCreate(phone="+9999", name="Coordinator", is_coordinator=True)
    )

    # Approve both
    approve_volunteer(db, "+1111", approver.id)
    approve_volunteer(db, "+2222", approver.id)

    # Verify none are pending
    pending = get_pending_volunteers(db)
    assert len(pending) == 0

    # Verify both are approved
    approved = list_volunteers(db, status="approved")
    assert len(approved) == 3  # vol1, vol2, and approver


def test_reject_then_approve(db):
    """Test rejecting and then approving a volunteer."""
    vol = create_volunteer(
        db, VolunteerCreate(phone="+1111", name="Alice", status="pending")
    )
    approver = create_volunteer(
        db, VolunteerCreate(phone="+9999", name="Coordinator", is_coordinator=True)
    )

    # Reject first
    rejected = reject_volunteer(db, "+1111")
    assert rejected.status == "rejected"

    # Now approve (this should work - status can change)
    approved = approve_volunteer(db, "+1111", approver.id)
    assert approved.status == "approved"
    assert approved.approved_by == approver.id
