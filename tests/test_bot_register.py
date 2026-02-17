"""Tests for p6-03: Registration bot command handler."""

from fastapi.testclient import TestClient

from app.db import get_db_connection, create_tables
from app.main import app
from app.models.volunteer import VolunteerCreate, create_volunteer
from app.bot.handlers.registration import handle_register
from app.bot.parser import parse_message


class TestRegistrationHandler:
    """Test the handle_register function."""

    def test_new_volunteer_registration(self):
        """Unknown phone should register and create pending volunteer."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_register(db, "1234567890", {"name": "Alice"})
        assert "Thank you Alice" in result
        assert "pending approval" in result

        # Verify volunteer was created
        row = db.execute(
            "SELECT * FROM volunteers WHERE phone = ?", ("1234567890",)
        ).fetchone()
        assert row is not None
        assert row["name"] == "Alice"
        assert row["status"] == "pending"

    def test_phone_already_registered_pending(self):
        """If phone already registered as pending, return appropriate message."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create pending volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Bob", is_coordinator=False, status="pending"
            ),
        )

        result = handle_register(db, vol.phone, {"name": "Bob"})
        assert "already registered" in result
        assert "pending approval" in result

    def test_phone_already_registered_approved(self):
        """If phone already registered as approved, return appropriate message."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create approved volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Charlie", is_coordinator=False, status="approved"
            ),
        )

        result = handle_register(db, vol.phone, {"name": "Charlie"})
        assert "already registered" in result
        assert "Charlie" in result

    def test_phone_already_registered_rejected(self):
        """If phone already registered as rejected, return rejection message."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create rejected volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="David", is_coordinator=False, status="rejected"
            ),
        )

        result = handle_register(db, vol.phone, {"name": "David"})
        assert "rejected" in result

    def test_register_without_name(self):
        """Registration without name should prompt for name."""
        db = get_db_connection(":memory:")
        create_tables(db)

        result = handle_register(db, "1234567890", {})
        assert "provide your name" in result.lower()


class TestRegistrationParser:
    """Test parsing of register command."""

    def test_parse_register_command(self):
        """Should parse 'register John Smith' correctly."""
        parsed = parse_message("register John Smith")
        assert parsed.command_type == "register"
        assert parsed.args["name"] == "john smith"

    def test_parse_register_single_name(self):
        """Should parse single name registration."""
        parsed = parse_message("register Alice")
        assert parsed.command_type == "register"
        assert parsed.args["name"] == "alice"

    def test_parse_register_without_name(self):
        """Should return error for register without name."""
        parsed = parse_message("register")
        assert hasattr(parsed, "suggestions")  # It's a ParseError
        assert "register" in " ".join(parsed.suggestions).lower()


class TestDispatcherRegistration:
    """Test the updated dispatcher for registration handling."""

    def test_unknown_phone_no_command_shows_registration_prompt(self):
        """Unknown phone without register command gets registration prompt."""
        db = get_db_connection(":memory:")
        create_tables(db)

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming", json={"phone": "1234567890", "message": "help"}
        )
        # Unknown phone: should show help first time, which includes register
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data

    def test_unknown_phone_can_register(self):
        """Unknown phone can register using register command."""
        db = get_db_connection(":memory:")
        create_tables(db)

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "1234567890", "message": "register Alice"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Thank you" in data["reply"]
        assert "alice" in data["reply"].lower()
        assert "pending approval" in data["reply"]

    def test_unknown_phone_invalid_command_prompts_register(self):
        """Unknown phone with invalid command gets registration prompt."""
        db = get_db_connection(":memory:")
        create_tables(db)

        client = TestClient(app)
        app.state.db = db

        response = client.post(
            "/api/wa/incoming",
            json={"phone": "1234567890", "message": "signup 2026-03-01 kakad"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "register" in data["reply"].lower()

    def test_approved_volunteer_can_still_use_bot(self):
        """Approved volunteer can use bot commands."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create approved volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Alice", is_coordinator=False, status="approved"
            ),
        )

        client = TestClient(app)
        app.state.db = db

        # Should be able to use commands
        response = client.post(
            "/api/wa/incoming", json={"phone": vol.phone, "message": "help"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Available commands" in data["reply"]

    def test_pending_volunteer_cannot_use_bot(self):
        """Pending volunteer should not get auth context."""
        db = get_db_connection(":memory:")
        create_tables(db)

        # Create pending volunteer
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone="1234567890", name="Bob", is_coordinator=False, status="pending"
            ),
        )

        client = TestClient(app)
        app.state.db = db

        # Should be treated as unauthenticated
        response = client.post(
            "/api/wa/incoming",
            json={"phone": vol.phone, "message": "signup 2026-03-01 kakad"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "register" in data["reply"].lower() or "not registered" in data["reply"].lower()
