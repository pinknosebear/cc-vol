from app.bot.auth import get_volunteer_context, VolunteerContext
from app.models.volunteer import create_volunteer, VolunteerCreate


def test_coordinator_returns_is_coordinator_true(db):
    create_volunteer(db, VolunteerCreate(phone="1111", name="Alice", is_coordinator=True))
    ctx = get_volunteer_context(db, "1111")
    assert ctx is not None
    assert ctx.is_coordinator is True


def test_regular_volunteer_returns_is_coordinator_false(db):
    create_volunteer(db, VolunteerCreate(phone="2222", name="Bob", is_coordinator=False))
    ctx = get_volunteer_context(db, "2222")
    assert ctx is not None
    assert ctx.is_coordinator is False


def test_unknown_phone_returns_none(db):
    ctx = get_volunteer_context(db, "9999")
    assert ctx is None


def test_context_fields_match_volunteer(db):
    vol = create_volunteer(db, VolunteerCreate(phone="3333", name="Carol", is_coordinator=True))
    ctx = get_volunteer_context(db, "3333")
    assert isinstance(ctx, VolunteerContext)
    assert ctx.volunteer_id == vol.id
    assert ctx.phone == vol.phone
    assert ctx.is_coordinator == vol.is_coordinator
