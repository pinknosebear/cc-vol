import os
import sqlite3
import re
from typing import Optional
from urllib.parse import urlparse, urlunparse
import httpx

from app.models.notification import NotificationCreate, create_notification, mark_sent, mark_error
from app.models.volunteer import get_volunteer_by_phone, Volunteer, normalize_phone


def _normalized_service_url(raw: Optional[str], default_url: str, default_internal_port: int) -> str:
    """Normalize env-provided service URL values into a valid base URL.

    Handles common Railway UI input issues:
    - missing protocol (e.g. wa-bridge.railway.internal)
    - dangling colon (e.g. http://wa-bridge.railway.internal:)
    - accidental suffix labels (e.g. "(line 8080)")
    """
    value = (raw or "").strip().strip('"').strip("'")
    if not value:
        return default_url

    value = re.sub(r"\s*\(line\s*\d+\)\s*$", "", value, flags=re.IGNORECASE)

    if "://" not in value:
        value = f"http://{value}"

    parsed = urlparse(value)
    if not parsed.hostname:
        return default_url

    scheme = parsed.scheme or "http"
    hostname = parsed.hostname

    try:
        port = parsed.port
    except ValueError:
        port = None

    if port is None and hostname.endswith(".railway.internal"):
        port = default_internal_port

    netloc = hostname if port is None else f"{hostname}:{port}"
    path = (parsed.path or "").rstrip("/")

    return urlunparse((scheme, netloc, path, "", "", ""))


def send_message(
    db: sqlite3.Connection,
    volunteer_id: int,
    message: str,
    notification_type: str = "alert",
) -> dict:
    """
    Send a message to a volunteer via WA Bridge.

    Steps:
    1. Look up volunteer by ID to get phone
    2. Create notification record in DB
    3. Call WA_BRIDGE_URL POST /send with phone and message
    4. Mark notification as sent or error

    Returns:
        dict with keys: success (bool), notification_id (int), error (str or None)
    """
    # Step 1: Look up volunteer by ID
    volunteer = _get_volunteer_by_id(db, volunteer_id)
    if volunteer is None:
        return {"success": False, "notification_id": None, "error": f"Volunteer {volunteer_id} not found"}

    # Step 2: Create notification record
    notif_data = NotificationCreate(
        volunteer_id=volunteer_id,
        type=notification_type,
        message=message,
    )
    notification = create_notification(db, notif_data)

    # Step 3: Call WA Bridge
    wa_bridge_url = _normalized_service_url(
        os.getenv("WA_BRIDGE_URL"),
        default_url="http://localhost:3000",
        default_internal_port=8080,
    )
    endpoint = f"{wa_bridge_url}/send"

    payload = {
        "phone": normalize_phone(volunteer.phone),
        "message": message,
    }

    try:
        response = httpx.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()

        # Step 4a: Mark as sent
        mark_sent(db, notification.id)
        return {
            "success": True,
            "notification_id": notification.id,
            "error": None,
        }
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        error_msg = str(e)
        mark_error(db, notification.id, error_msg)
        return {
            "success": False,
            "notification_id": notification.id,
            "error": error_msg,
        }


def _get_volunteer_by_id(db: sqlite3.Connection, volunteer_id: int) -> Optional[Volunteer]:
    """Helper to get a volunteer by ID (not by phone)."""
    row = db.execute(
        "SELECT * FROM volunteers WHERE id = ?", (volunteer_id,)
    ).fetchone()
    if row is None:
        return None

    from app.models.volunteer import _row_to_volunteer
    return _row_to_volunteer(row)
