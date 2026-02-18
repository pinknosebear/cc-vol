"""Volunteer registration command handler."""

from __future__ import annotations

import sqlite3

from app.bot.auth import VolunteerContext
from app.models.volunteer import (
    VolunteerCreate,
    create_volunteer,
    get_volunteer_by_phone,
    get_pending_volunteers,
    approve_volunteer,
    reject_volunteer,
)
from app.notifications.sender import send_message


def handle_register(
    db: sqlite3.Connection,
    phone: str,
    args: dict,
) -> str:
    """Process a volunteer registration request.

    Parameters
    ----------
    db:
        SQLite connection with Row factory.
    phone:
        Phone number attempting to register.
    args:
        Dict with key ``name`` (str).

    Returns
    -------
    str
        A user-facing message describing the outcome.
    """
    name: str = args.get("name", "").strip()

    if not name:
        return "Please provide your name. Send: register <your name>"

    # Check if phone already registered
    existing = get_volunteer_by_phone(db, phone)
    if existing is not None:
        if existing.status == "pending":
            return f"You already registered as {existing.name} and are pending approval."
        elif existing.status == "approved":
            return f"You're already registered as {existing.name}."
        else:  # rejected
            return f"Your registration was rejected. Please contact support."

    # Create new pending volunteer
    try:
        vol = create_volunteer(
            db,
            VolunteerCreate(
                phone=phone,
                name=name,
                is_coordinator=False,
                status="pending",
            ),
        )
        return f"Thank you {name}! Your registration is pending approval. You'll be notified when approved."
    except Exception as e:
        return f"Registration failed. Please try again later. Error: {str(e)}"


def handle_pending(
    db: sqlite3.Connection,
    context: VolunteerContext,
    args: dict,
) -> str:
    """List all pending registrations.

    Parameters
    ----------
    db:
        SQLite connection with Row factory.
    context:
        Coordinator's volunteer context.
    args:
        Empty dict (no arguments needed).

    Returns
    -------
    str
        A formatted list of pending volunteers or a message if none.
    """
    pending = get_pending_volunteers(db)

    if not pending:
        return "No pending registrations."

    lines = ["*Pending Registrations*"]
    for vol in pending:
        lines.append(f"- {vol.name} ({vol.phone})")

    return "\n".join(lines)


def handle_approve(
    db: sqlite3.Connection,
    context: VolunteerContext,
    args: dict,
) -> str:
    """Approve a volunteer registration.

    Parameters
    ----------
    db:
        SQLite connection with Row factory.
    context:
        Coordinator's volunteer context.
    args:
        Dict with key ``phone`` (str).

    Returns
    -------
    str
        A user-facing message describing the outcome.
    """
    phone: str = args.get("phone", "").strip()

    if not phone:
        return "Please provide the phone number. Send: approve <phone>"

    # Check if volunteer exists
    vol = get_volunteer_by_phone(db, phone)
    if vol is None:
        return f"No volunteer found with phone {phone}"

    # Check if already approved
    if vol.status == "approved":
        return f"{vol.name} is already approved."

    # Check if rejected
    if vol.status == "rejected":
        return f"{vol.name} has been rejected and cannot be approved."

    # Approve the volunteer
    try:
        approved = approve_volunteer(db, phone, context.volunteer_id)
        if approved is None:
            return f"Could not approve {phone}. Please try again."

        welcome_text = (
            f"Welcome {approved.name}! You're approved to volunteer. "
            "Reply 'help' to see available commands."
        )
        result = send_message(
            db,
            approved.id,
            welcome_text,
            notification_type="welcome",
        )
        if result["success"]:
            return f"Approved {approved.name} ({phone}). Welcome message sent."
        return (
            f"Approved {approved.name} ({phone}). "
            f"Welcome message failed: {result['error']}"
        )
    except Exception as e:
        return f"Approval failed. Error: {str(e)}"


def handle_reject(
    db: sqlite3.Connection,
    context: VolunteerContext,
    args: dict,
) -> str:
    """Reject a volunteer registration.

    Parameters
    ----------
    db:
        SQLite connection with Row factory.
    context:
        Coordinator's volunteer context.
    args:
        Dict with key ``phone`` (str).

    Returns
    -------
    str
        A user-facing message describing the outcome.
    """
    phone: str = args.get("phone", "").strip()

    if not phone:
        return "Please provide the phone number. Send: reject <phone>"

    # Check if volunteer exists
    vol = get_volunteer_by_phone(db, phone)
    if vol is None:
        return f"No volunteer found with phone {phone}"

    # Check if already rejected
    if vol.status == "rejected":
        return f"{vol.name} is already rejected."

    # Check if already approved
    if vol.status == "approved":
        return f"{vol.name} is already approved and cannot be rejected."

    # Reject the volunteer
    try:
        rejected = reject_volunteer(db, phone)
        if rejected is None:
            return f"Could not reject {phone}. Please try again."

        return f"Rejected {rejected.name} ({phone})."
    except Exception as e:
        return f"Rejection failed. Error: {str(e)}"
