import pytest
import sqlite3
from datetime import datetime

from app.models.notification import (
    NotificationCreate,
    Notification,
    create_notification,
    get_notification,
    list_notifications_by_volunteer,
    mark_sent,
    mark_acknowledged,
    mark_error,
    _row_to_notification,
)
from app.models.volunteer import create_volunteer, VolunteerCreate


class TestNotificationModel:
    """Test Notification Pydantic model."""

    def test_notification_create_minimal(self):
        """Test creating a NotificationCreate with required fields."""
        notif = NotificationCreate(
            volunteer_id=1,
            type="reminder",
            message="Test message",
        )
        assert notif.volunteer_id == 1
        assert notif.type == "reminder"
        assert notif.message == "Test message"

    def test_notification_create_valid_types(self):
        """Test that all valid notification types are accepted."""
        valid_types = ["reminder", "escalation", "welcome", "alert"]
        for notif_type in valid_types:
            notif = NotificationCreate(
                volunteer_id=1,
                type=notif_type,
                message="Test",
            )
            assert notif.type == notif_type

    def test_notification_create_invalid_type(self):
        """Test that invalid notification types are rejected."""
        with pytest.raises(ValueError):
            NotificationCreate(
                volunteer_id=1,
                type="invalid_type",
                message="Test",
            )

    def test_notification_model(self):
        """Test the Notification model with all fields."""
        notif = Notification(
            id=1,
            volunteer_id=2,
            type="alert",
            message="Test alert",
            sent_at=datetime(2026, 2, 17, 10, 0, 0),
            ack_at=None,
            error=None,
        )
        assert notif.id == 1
        assert notif.volunteer_id == 2
        assert notif.type == "alert"
        assert notif.message == "Test alert"
        assert notif.sent_at is not None
        assert notif.ack_at is None
        assert notif.error is None

    def test_notification_model_with_error(self):
        """Test Notification model with error field set."""
        notif = Notification(
            id=1,
            volunteer_id=2,
            type="alert",
            message="Test alert",
            sent_at=None,
            ack_at=None,
            error="Connection timeout",
        )
        assert notif.error == "Connection timeout"


class TestNotificationCRUD:
    """Test notification CRUD operations."""

    def test_create_notification(self, db):
        """Test creating a notification."""
        # First create a volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Create a notification
        notif_data = NotificationCreate(
            volunteer_id=volunteer.id,
            type="reminder",
            message="Test reminder message",
        )
        notification = create_notification(db, notif_data)

        assert notification.id is not None
        assert notification.volunteer_id == volunteer.id
        assert notification.type == "reminder"
        assert notification.message == "Test reminder message"
        assert notification.sent_at is None
        assert notification.ack_at is None
        assert notification.error is None

    def test_get_notification(self, db):
        """Test retrieving a notification by ID."""
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        notif_data = NotificationCreate(
            volunteer_id=volunteer.id,
            type="alert",
            message="Alert message",
        )
        created = create_notification(db, notif_data)

        retrieved = get_notification(db, created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.volunteer_id == volunteer.id
        assert retrieved.type == "alert"
        assert retrieved.message == "Alert message"

    def test_get_notification_not_found(self, db):
        """Test getting a notification that doesn't exist."""
        result = get_notification(db, 999)
        assert result is None

    def test_list_notifications_by_volunteer(self, db):
        """Test listing all notifications for a volunteer."""
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Create multiple notifications
        types = ["reminder", "alert", "welcome"]
        for i, notif_type in enumerate(types):
            notif_data = NotificationCreate(
                volunteer_id=volunteer.id,
                type=notif_type,
                message=f"Message {i}",
            )
            create_notification(db, notif_data)

        notifications = list_notifications_by_volunteer(db, volunteer.id)
        assert len(notifications) == 3
        # Should be ordered by ID DESC (most recent first)
        assert notifications[0].type == types[2]  # Last created should be first
        assert notifications[1].type == types[1]
        assert notifications[2].type == types[0]

    def test_list_notifications_empty(self, db):
        """Test listing notifications when none exist for volunteer."""
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        notifications = list_notifications_by_volunteer(db, volunteer.id)
        assert notifications == []

    def test_mark_sent(self, db):
        """Test marking a notification as sent."""
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        notif_data = NotificationCreate(
            volunteer_id=volunteer.id,
            type="reminder",
            message="Test message",
        )
        notification = create_notification(db, notif_data)
        assert notification.sent_at is None

        updated = mark_sent(db, notification.id)
        assert updated is not None
        assert updated.sent_at is not None

    def test_mark_acknowledged(self, db):
        """Test marking a notification as acknowledged."""
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        notif_data = NotificationCreate(
            volunteer_id=volunteer.id,
            type="reminder",
            message="Test message",
        )
        notification = create_notification(db, notif_data)
        assert notification.ack_at is None

        updated = mark_acknowledged(db, notification.id)
        assert updated is not None
        assert updated.ack_at is not None

    def test_mark_error(self, db):
        """Test marking a notification with an error."""
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        notif_data = NotificationCreate(
            volunteer_id=volunteer.id,
            type="alert",
            message="Test message",
        )
        notification = create_notification(db, notif_data)
        assert notification.error is None

        error_msg = "Connection timeout to WA Bridge"
        updated = mark_error(db, notification.id, error_msg)
        assert updated is not None
        assert updated.error == error_msg

    def test_mark_sent_nonexistent(self, db):
        """Test marking a nonexistent notification returns None."""
        result = mark_sent(db, 999)
        assert result is None

    def test_mark_acknowledged_nonexistent(self, db):
        """Test acknowledging a nonexistent notification returns None."""
        result = mark_acknowledged(db, 999)
        assert result is None

    def test_mark_error_nonexistent(self, db):
        """Test marking error on nonexistent notification returns None."""
        result = mark_error(db, 999, "Some error")
        assert result is None
