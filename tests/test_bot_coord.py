"""Tests for coordinator bot command handlers."""

from datetime import date

from app.bot.auth import VolunteerContext
from app.bot.handlers.coordinator import handle_status, handle_gaps, handle_find_sub


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COORD_CTX = VolunteerContext(volunteer_id=1, phone="+0000", is_coordinator=True)


def _seed_shift(db, shift_date: str, shift_type: str, capacity: int) -> int:
    cursor = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        (shift_date, shift_type, capacity),
    )
    db.commit()
    return cursor.lastrowid


def _seed_volunteer(db, phone: str, name: str) -> int:
    cursor = db.execute(
        "INSERT INTO volunteers (phone, name) VALUES (?, ?)",
        (phone, name),
    )
    db.commit()
    return cursor.lastrowid


def _seed_signup(db, volunteer_id: int, shift_id: int):
    db.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (volunteer_id, shift_id),
    )
    db.commit()


# ---------------------------------------------------------------------------
# handle_status
# ---------------------------------------------------------------------------


class TestHandleStatus:
    def test_shows_filled_and_open_status(self, db):
        """Shifts with correct filled/open status."""
        sid1 = _seed_shift(db, "2026-02-15", "kakad", 2)
        sid2 = _seed_shift(db, "2026-02-15", "robe", 2)

        v1 = _seed_volunteer(db, "+1111", "Alice")
        v2 = _seed_volunteer(db, "+2222", "Bob")

        # Fill the kakad shift
        _seed_signup(db, v1, sid1)
        _seed_signup(db, v2, sid1)

        # Only 1 signup for robe
        _seed_signup(db, v1, sid2)

        result = handle_status(db, COORD_CTX, {"date": date(2026, 2, 15)})

        assert "2026-02-15" in result
        assert "kakad: 2/2 (filled)" in result
        assert "robe: 1/2 (open)" in result

    def test_no_shifts_returns_empty_message(self, db):
        """Date with no shifts returns informational message."""
        result = handle_status(db, COORD_CTX, {"date": date(2026, 3, 1)})
        assert result == "No shifts found for 2026-03-01"


# ---------------------------------------------------------------------------
# handle_gaps
# ---------------------------------------------------------------------------


class TestHandleGaps:
    def test_unfilled_shifts_listed(self, db):
        """Shifts with gaps are listed with gap size."""
        sid = _seed_shift(db, "2026-02-10", "kakad", 3)
        vid = _seed_volunteer(db, "+1111", "Alice")
        _seed_signup(db, vid, sid)

        result = handle_gaps(db, COORD_CTX, {"month": "2026-02"})

        assert "2026-02-10" in result
        assert "kakad" in result
        assert "2 needed" in result

    def test_all_filled_returns_success(self, db):
        """When all shifts are filled, return success message."""
        sid = _seed_shift(db, "2026-02-10", "robe", 2)
        v1 = _seed_volunteer(db, "+1111", "Alice")
        v2 = _seed_volunteer(db, "+2222", "Bob")
        _seed_signup(db, v1, sid)
        _seed_signup(db, v2, sid)

        result = handle_gaps(db, COORD_CTX, {"month": "2026-02"})
        assert result == "All shifts filled for 2026-02!"


# ---------------------------------------------------------------------------
# handle_find_sub
# ---------------------------------------------------------------------------


class TestHandleFindSub:
    def test_returns_available_volunteers(self, db):
        """Volunteers under the limit who aren't signed up should appear."""
        sid = _seed_shift(db, "2026-02-15", "kakad", 3)
        vid = _seed_volunteer(db, "+1111", "Alice")

        result = handle_find_sub(db, COORD_CTX, {"date": date(2026, 2, 15), "type": "kakad"})

        assert "Alice" in result
        assert "+1111" in result

    def test_excludes_already_signed_up(self, db):
        """Volunteers already signed up for the shift should not appear."""
        sid = _seed_shift(db, "2026-02-15", "kakad", 3)
        v1 = _seed_volunteer(db, "+1111", "Alice")
        v2 = _seed_volunteer(db, "+2222", "Bob")

        # Alice is already signed up
        _seed_signup(db, v1, sid)

        result = handle_find_sub(db, COORD_CTX, {"date": date(2026, 2, 15), "type": "kakad"})

        assert "Alice" not in result
        assert "Bob" in result

    def test_excludes_volunteers_at_limit(self, db):
        """Volunteers with 8+ signups in the month should not appear."""
        target_sid = _seed_shift(db, "2026-02-15", "kakad", 3)
        vid = _seed_volunteer(db, "+1111", "Alice")

        # Give Alice 8 signups in Feb across other shifts
        for day in range(1, 9):
            stype = "kakad" if day % 2 == 0 else "robe"
            sid = _seed_shift(db, f"2026-02-{day:02d}", stype, 3)
            _seed_signup(db, vid, sid)

        result = handle_find_sub(db, COORD_CTX, {"date": date(2026, 2, 15), "type": "kakad"})
        assert result == "No available volunteers found"

    def test_no_available_returns_message(self, db):
        """When no volunteers are available, return informational message."""
        sid = _seed_shift(db, "2026-02-15", "kakad", 3)
        # Only volunteer is already signed up
        vid = _seed_volunteer(db, "+1111", "Alice")
        _seed_signup(db, vid, sid)

        result = handle_find_sub(db, COORD_CTX, {"date": date(2026, 2, 15), "type": "kakad"})
        assert result == "No available volunteers found"
