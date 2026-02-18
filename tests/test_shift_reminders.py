from datetime import date
from unittest.mock import patch

from app.db import create_tables, get_db_connection
from app.notifications.reminders import _send_reminders_for_date, _notification_exists


def test_send_reminders_for_date_calls_sender():
    db = get_db_connection(":memory:")
    create_tables(db)

    vol_id = db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator, status) VALUES (?, ?, ?, ?)",
        ("+15550001111", "Alice", 0, "approved"),
    ).lastrowid
    shift_id = db.execute(
        "INSERT INTO shifts (date, shift_type, capacity) VALUES (?, ?, ?)",
        ("2026-02-19", "kakad", 1),
    ).lastrowid
    db.execute(
        "INSERT INTO signups (volunteer_id, shift_id) VALUES (?, ?)",
        (vol_id, shift_id),
    )
    db.commit()

    with patch("app.notifications.reminders.send_message") as mock_send:
        _send_reminders_for_date(db, date(2026, 2, 19), 1)
        assert mock_send.call_count == 1
        _, _, message = mock_send.call_args[0]
        assert "tomorrow" in message


def test_notification_exists_checks_message():
    db = get_db_connection(":memory:")
    create_tables(db)
    vol_id = db.execute(
        "INSERT INTO volunteers (phone, name, is_coordinator, status) VALUES (?, ?, ?, ?)",
        ("+15550002222", "Bob", 0, "approved"),
    ).lastrowid
    db.execute(
        "INSERT INTO notifications (volunteer_id, type, message) VALUES (?, ?, ?)",
        (vol_id, "reminder", "hello"),
    )
    db.commit()

    assert _notification_exists(db, vol_id, "hello") is True
    assert _notification_exists(db, vol_id, "different") is False
