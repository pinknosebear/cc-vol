"""Tests for p6-04: Coordinator approve/reject commands."""

from fastapi.testclient import TestClient

from app.db import get_db_connection, create_tables
from app.main import app
from app.models.volunteer import VolunteerCreate, create_volunteer
from app.bot.handlers.registration import (
    handle_approve,
    handle_reject,
    handle_pending,
)
from app.bot.auth import VolunteerContext
from app.bot.parser import parse_message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COORD_CTX = VolunteerContext(volunteer_id=1, phone="+0000", is_coordinator=True)


def _add_volunteer(db, phone: str, name: str, status: str = "approved") -> int:
    """Helper to add a volunteer with a given status."""
    vol = create_volunteer(
        db,
        VolunteerCreate(
            phone=phone, name=name, is_coordinator=False, status=status
        ),
    )
    return vol.id


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------


class TestApproveRejectParser:
    """Test parsing of approve/reject/pending commands."""

    def test_parse_approve_command(self):
        """Should parse 'approve +1234567890' correctly."""
        parsed = parse_message("approve +1234567890")
        assert parsed.command_type == "approve"
        assert parsed.args["phone"] == "+1234567890"

    def test_parse_reject_command(self):
        """Should parse 'reject +1234567890' correctly."""
        parsed = parse_message("reject +1234567890")
        assert parsed.command_type == "reject"
        assert parsed.args["phone"] == "+1234567890"

    def test_parse_pending_command(self):
        """Should parse 'pending' correctly."""
        parsed = parse_message("pending")
        assert parsed.command_type == "pending"
        assert parsed.args == {}

    def test_parse_approve_without_phone(self):
        """Should return error for approve without phone."""
        parsed = parse_message("approve")
        assert hasattr(parsed, "suggestions")  # It's a ParseError
        assert "approve" in " ".join(parsed.suggestions).lower()

    def test_parse_reject_without_phone(self):
        """Should return error for reject without phone."""
        parsed = parse_message("reject")
        assert hasattr(parsed, "suggestions")  # It's a ParseError
        assert "reject" in " ".join(parsed.suggestions).lower()


# ---------------------------------------------------------------------------
# handle_approve Tests
# ---------------------------------------------------------------------------


class TestHandleApprove:
    def test_approve_pending_volunteer(self):
        """Should approve a pending volunteer."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create pending volunteer
        _add_volunteer(db, "+1111111111", "Alice", status="pending")

        result = handle_approve(db, COORD_CTX, {"phone": "+1111111111"})
        assert "Approved" in result
        assert "Alice" in result
        assert "+1111111111" in result

        # Verify status changed in DB
        row = db.execute(
            "SELECT status FROM volunteers WHERE phone = ?", ("+1111111111",)
        ).fetchone()
        assert row["status"] == "approved"

    def test_approve_already_approved(self):
        """Should return message if already approved."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+2222222222", "Bob", status="approved")

        result = handle_approve(db, COORD_CTX, {"phone": "+2222222222"})
        assert "already approved" in result

    def test_approve_rejected_volunteer(self):
        """Should return error if volunteer is rejected."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+3333333333", "Charlie", status="rejected")

        result = handle_approve(db, COORD_CTX, {"phone": "+3333333333"})
        assert "rejected" in result and "cannot be approved" in result

    def test_approve_nonexistent_volunteer(self):
        """Should return error if volunteer not found."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_approve(db, COORD_CTX, {"phone": "+9999999999"})
        assert "No volunteer found" in result

    def test_approve_without_phone(self):
        """Should prompt for phone if not provided."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_approve(db, COORD_CTX, {"phone": ""})
        assert "provide the phone number" in result.lower()


# ---------------------------------------------------------------------------
# handle_reject Tests
# ---------------------------------------------------------------------------


class TestHandleReject:
    def test_reject_pending_volunteer(self):
        """Should reject a pending volunteer."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+1111111111", "Alice", status="pending")

        result = handle_reject(db, COORD_CTX, {"phone": "+1111111111"})
        assert "Rejected" in result
        assert "Alice" in result
        assert "+1111111111" in result

        # Verify status changed in DB
        row = db.execute(
            "SELECT status FROM volunteers WHERE phone = ?", ("+1111111111",)
        ).fetchone()
        assert row["status"] == "rejected"

    def test_reject_already_rejected(self):
        """Should return message if already rejected."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+2222222222", "Bob", status="rejected")

        result = handle_reject(db, COORD_CTX, {"phone": "+2222222222"})
        assert "already rejected" in result

    def test_reject_approved_volunteer(self):
        """Should return error if volunteer is already approved."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+3333333333", "Charlie", status="approved")

        result = handle_reject(db, COORD_CTX, {"phone": "+3333333333"})
        assert "already approved" in result and "cannot be rejected" in result

    def test_reject_nonexistent_volunteer(self):
        """Should return error if volunteer not found."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_reject(db, COORD_CTX, {"phone": "+9999999999"})
        assert "No volunteer found" in result

    def test_reject_without_phone(self):
        """Should prompt for phone if not provided."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_reject(db, COORD_CTX, {"phone": ""})
        assert "provide the phone number" in result.lower()


# ---------------------------------------------------------------------------
# handle_pending Tests
# ---------------------------------------------------------------------------


class TestHandlePending:
    def test_list_pending_volunteers(self):
        """Should list all pending volunteers."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+1111111111", "Alice", status="pending")
        _add_volunteer(db, "+2222222222", "Bob", status="pending")
        _add_volunteer(db, "+3333333333", "Charlie", status="approved")

        result = handle_pending(db, COORD_CTX, {})

        assert "Pending Registrations" in result
        assert "Alice" in result
        assert "+1111111111" in result
        assert "Bob" in result
        assert "+2222222222" in result
        # Charlie should not appear (not pending)
        assert "Charlie" not in result

    def test_no_pending_volunteers(self):
        """Should return message if no pending volunteers."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+1111111111", "Alice", status="approved")

        result = handle_pending(db, COORD_CTX, {})
        assert result == "No pending registrations."

    def test_pending_empty_database(self):
        """Should return message if database is empty."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_pending(db, COORD_CTX, {})
        assert result == "No pending registrations."


# ---------------------------------------------------------------------------
# Dispatcher Tests
# ---------------------------------------------------------------------------


class TestApproveRejectDispatcher:
    """Test coordinator commands through the dispatcher endpoint."""

    def test_coordinator_can_use_approve(self):
        """Coordinator should be able to use approve command."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create coordinator and pending volunteer
        _add_volunteer(db, "+0000000000", "Coordinator", status="approved")
        _update_volunteer_is_coordinator(db, "+0000000000", True)
        _add_volunteer(db, "+1111111111", "Alice", status="pending")

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "+0000000000", "message": "approve +1111111111"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert "Approved" in reply
        assert "Alice" in reply

    def test_non_coordinator_cannot_approve(self):
        """Non-coordinator should get error for approve command."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+1111111111", "Regular Vol", status="approved")
        _add_volunteer(db, "+2222222222", "Alice", status="pending")

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "+1111111111", "message": "approve +2222222222"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert "coordinators only" in reply.lower()

    def test_coordinator_can_use_reject(self):
        """Coordinator should be able to use reject command."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+0000000000", "Coordinator", status="approved")
        _update_volunteer_is_coordinator(db, "+0000000000", True)
        _add_volunteer(db, "+1111111111", "Bob", status="pending")

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "+0000000000", "message": "reject +1111111111"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert "Rejected" in reply
        assert "Bob" in reply

    def test_coordinator_can_use_pending(self):
        """Coordinator should be able to use pending command."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+0000000000", "Coordinator", status="approved")
        _update_volunteer_is_coordinator(db, "+0000000000", True)
        _add_volunteer(db, "+1111111111", "Alice", status="pending")

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "+0000000000", "message": "pending"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert "Pending Registrations" in reply or "pending" in reply.lower()
        assert "Alice" in reply

    def test_non_coordinator_cannot_see_pending(self):
        """Non-coordinator should get error for pending command."""
        db = get_db_connection(":memory:")
        create_tables(db)

        _add_volunteer(db, "+1111111111", "Regular Vol", status="approved")

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "+1111111111", "message": "pending"},
        )
        assert response.status_code == 200
        reply = response.json()["reply"]
        assert "coordinators only" in reply.lower()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _update_volunteer_is_coordinator(db, phone: str, is_coordinator: bool):
    """Helper to update a volunteer's is_coordinator flag."""
    db.execute(
        "UPDATE volunteers SET is_coordinator = ? WHERE phone = ?",
        (is_coordinator, phone),
    )
    db.commit()
