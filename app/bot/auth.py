from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.models.volunteer import get_volunteer_by_phone


@dataclass
class VolunteerContext:
    volunteer_id: int
    phone: str
    is_coordinator: bool


def get_volunteer_context(
    db: sqlite3.Connection, phone: str
) -> VolunteerContext | None:
    """Look up a volunteer by phone and return their context.

    Returns None if the phone number is not registered or not approved.
    """
    volunteer = get_volunteer_by_phone(db, phone)
    if volunteer is None or volunteer.status != "approved":
        return None
    return VolunteerContext(
        volunteer_id=volunteer.id,
        phone=volunteer.phone,
        is_coordinator=volunteer.is_coordinator,
    )
