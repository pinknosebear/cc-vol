import pytest
import os
from unittest.mock import patch, MagicMock
import httpx

from app.notifications.sender import send_message
from app.models.volunteer import create_volunteer, VolunteerCreate
from app.models.notification import get_notification


class TestSendMessage:
    """Test the send_message service."""

    def test_send_message_volunteer_not_found(self, db):
        """Test sending message to nonexistent volunteer."""
        result = send_message(
            db,
            volunteer_id=999,
            message="Test message",
            notification_type="alert",
        )
        assert result["success"] is False
        assert result["notification_id"] is None
        assert "not found" in result["error"]

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_success(self, mock_post, db):
        """Test successful message sending."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock successful response
        mock_post.return_value = MagicMock(status_code=200)

        result = send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="reminder",
        )

        assert result["success"] is True
        assert result["notification_id"] is not None
        assert result["error"] is None

        # Verify the notification was marked as sent
        notification = get_notification(db, result["notification_id"])
        assert notification is not None
        assert notification.sent_at is not None
        assert notification.error is None

        # Verify WA Bridge was called with correct payload
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["phone"] == "+1234567890"
        assert call_args[1]["json"]["message"] == "Test message"

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_failure(self, mock_post, db):
        """Test message sending failure."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock failed response
        mock_post.side_effect = httpx.RequestError("Connection failed")

        result = send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="alert",
        )

        assert result["success"] is False
        assert result["notification_id"] is not None
        assert result["error"] is not None
        assert "Connection failed" in result["error"]

        # Verify the notification was marked with error
        notification = get_notification(db, result["notification_id"])
        assert notification is not None
        assert notification.sent_at is None
        assert notification.error is not None

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_timeout(self, mock_post, db):
        """Test message sending timeout."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock timeout
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        result = send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="alert",
        )

        assert result["success"] is False
        assert result["notification_id"] is not None
        assert "timed out" in result["error"]

    @patch.dict(os.environ, {"WA_BRIDGE_URL": "http://custom-bridge:3000"})
    @patch("app.notifications.sender.httpx.post")
    def test_send_message_custom_bridge_url(self, mock_post, db):
        """Test that custom WA_BRIDGE_URL is used."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock successful response
        mock_post.return_value = MagicMock(status_code=200)

        send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="alert",
        )

        # Verify correct URL was used
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == "http://custom-bridge:3000/send"

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_default_bridge_url(self, mock_post, db):
        """Test that default WA_BRIDGE_URL is used when env var not set."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock successful response
        mock_post.return_value = MagicMock(status_code=200)

        # Ensure WA_BRIDGE_URL is not set
        if "WA_BRIDGE_URL" in os.environ:
            del os.environ["WA_BRIDGE_URL"]

        send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="alert",
        )

        # Verify default URL was used
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == "http://localhost:3000/send"

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_notification_persisted(self, mock_post, db):
        """Test that notification record is persisted even on failure."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock failure
        mock_post.side_effect = httpx.RequestError("Failed")

        result = send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="escalation",
        )

        notif_id = result["notification_id"]
        assert notif_id is not None

        # Verify notification is in DB
        notification = get_notification(db, notif_id)
        assert notification is not None
        assert notification.volunteer_id == volunteer.id
        assert notification.type == "escalation"
        assert notification.message == "Test message"

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_different_types(self, mock_post, db):
        """Test sending messages with different notification types."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock successful response
        mock_post.return_value = MagicMock(status_code=200)

        types = ["reminder", "escalation", "welcome", "alert"]
        for notif_type in types:
            result = send_message(
                db,
                volunteer_id=volunteer.id,
                message=f"{notif_type} message",
                notification_type=notif_type,
            )

            assert result["success"] is True
            notification = get_notification(db, result["notification_id"])
            assert notification.type == notif_type

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_http_error(self, mock_post, db):
        """Test handling of HTTP errors."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock HTTP error
        mock_post.side_effect = httpx.HTTPStatusError("500 Server Error", request=MagicMock(), response=MagicMock())

        result = send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
            notification_type="alert",
        )

        assert result["success"] is False
        assert "500 Server Error" in result["error"]

    @patch("app.notifications.sender.httpx.post")
    def test_send_message_with_default_type(self, mock_post, db):
        """Test sending message with default notification type."""
        # Create volunteer
        vol_data = VolunteerCreate(phone="+1234567890", name="Test Volunteer")
        volunteer = create_volunteer(db, vol_data)

        # Mock successful response
        mock_post.return_value = MagicMock(status_code=200)

        # Don't specify notification_type, should default to "alert"
        result = send_message(
            db,
            volunteer_id=volunteer.id,
            message="Test message",
        )

        assert result["success"] is True
        notification = get_notification(db, result["notification_id"])
        assert notification.type == "alert"
