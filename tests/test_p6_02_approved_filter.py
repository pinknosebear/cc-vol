"""Tests for p6-02: Filter existing handlers by approved status."""

from datetime import date
from fastapi.testclient import TestClient

from app.db import get_db_connection, create_tables
from app.main import app
from app.models.volunteer import VolunteerCreate, create_volunteer
from app.models.shift import ShiftCreate, create_shift
from app.rules.validator import validate_signup
from app.bot.auth import get_volunteer_context


class TestBotAuthFiltering:
    """Bot auth should return None for non-approved volunteers."""

    def test_approved_volunteer_returns_context(self):
        """Approved volunteer should get context."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create an approved volunteer (default status)
        vol_data = VolunteerCreate(phone="1234567890", name="Alice", is_coordinator=False)
        vol = create_volunteer(db, vol_data)

        context = get_volunteer_context(db, vol.phone)
        assert context is not None
        assert context.volunteer_id == vol.id
        assert context.phone == vol.phone
        assert context.is_coordinator is False

    def test_pending_volunteer_returns_none(self):
        """Pending volunteer should not get context."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create a pending volunteer
        vol_data = VolunteerCreate(
            phone="1234567890", name="Bob", is_coordinator=False, status="pending"
        )
        vol = create_volunteer(db, vol_data)

        context = get_volunteer_context(db, vol.phone)
        assert context is None

    def test_rejected_volunteer_returns_none(self):
        """Rejected volunteer should not get context."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create a rejected volunteer
        vol_data = VolunteerCreate(
            phone="1234567890", name="Charlie", is_coordinator=False, status="rejected"
        )
        vol = create_volunteer(db, vol_data)

        context = get_volunteer_context(db, vol.phone)
        assert context is None


class TestAPIDVolunteerFiltering:
    """API GET /api/volunteers should filter by status."""

    def test_default_returns_only_approved(self):
        """Without ?status param, should return only approved volunteers."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create volunteers with different statuses
        approved = create_volunteer(
            db,
            VolunteerCreate(
                phone="1111111111", name="Alice", is_coordinator=False, status="approved"
            ),
        )
        pending = create_volunteer(
            db,
            VolunteerCreate(
                phone="2222222222", name="Bob", is_coordinator=False, status="pending"
            ),
        )
        rejected = create_volunteer(
            db,
            VolunteerCreate(
                phone="3333333333", name="Charlie", is_coordinator=False, status="rejected"
            ),
        )

        client = TestClient(app)
        app.state.db = db

        response = client.get("/api/volunteers")
        assert response.status_code == 200
        volunteers = response.json()

        # Should only have the approved volunteer
        assert len(volunteers) == 1
        assert volunteers[0]["phone"] == approved.phone
        assert volunteers[0]["status"] == "approved"

    def test_status_param_filters_by_status(self):
        """With ?status=pending, should return pending volunteers."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create volunteers with different statuses
        create_volunteer(
            db,
            VolunteerCreate(
                phone="1111111111", name="Alice", is_coordinator=False, status="approved"
            ),
        )
        pending = create_volunteer(
            db,
            VolunteerCreate(
                phone="2222222222", name="Bob", is_coordinator=False, status="pending"
            ),
        )

        client = TestClient(app)
        app.state.db = db

        response = client.get("/api/volunteers?status=pending")
        assert response.status_code == 200
        volunteers = response.json()

        # Should only have the pending volunteer
        assert len(volunteers) == 1
        assert volunteers[0]["phone"] == pending.phone
        assert volunteers[0]["status"] == "pending"


class TestValidatorApprovedFilter:
    """Signup validator should reject non-approved volunteers."""

    def test_approved_volunteer_passes_through_validator(self):
        """Approved volunteer should pass validator (if other rules allow)."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create an approved volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Alice", is_coordinator=False, status="approved"
            ),
        )

        # Create a shift with capacity
        shift = create_shift(db, ShiftCreate(date=date(2026, 3, 1), type="kakad", capacity=2))

        # Validation should pass (no violations)
        violations = validate_signup(db, vol.id, shift.id)
        # Should have no violation about approval status
        approval_violations = [v for v in violations if "not approved" in v.reason]
        assert len(approval_violations) == 0

    def test_pending_volunteer_rejected_by_validator(self):
        """Pending volunteer should be rejected by validator."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create a pending volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Bob", is_coordinator=False, status="pending"
            ),
        )

        # Create a shift with capacity
        shift = create_shift(db, ShiftCreate(date=date(2026, 3, 1), type="kakad", capacity=2))

        # Validation should reject with approval violation
        violations = validate_signup(db, vol.id, shift.id)
        assert len(violations) == 1
        assert "not approved" in violations[0].reason
        assert violations[0].allowed is False

    def test_rejected_volunteer_rejected_by_validator(self):
        """Rejected volunteer should be rejected by validator."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create a rejected volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Charlie", is_coordinator=False, status="rejected"
            ),
        )

        # Create a shift with capacity
        shift = create_shift(db, ShiftCreate(date=date(2026, 3, 1), type="kakad", capacity=2))

        # Validation should reject with approval violation
        violations = validate_signup(db, vol.id, shift.id)
        assert len(violations) == 1
        assert "not approved" in violations[0].reason
        assert violations[0].allowed is False
