"""Volunteer registration command handler."""

from __future__ import annotations

import sqlite3

from app.models.volunteer import VolunteerCreate, create_volunteer, get_volunteer_by_phone


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
