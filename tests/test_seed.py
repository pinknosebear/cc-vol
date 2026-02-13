"""Tests for app.seed — monthly shift seeding."""

from datetime import date

from app.seed import seed_month
from app.models.shift import get_shifts_by_month, get_robe_capacity


def test_seed_feb_2026_creates_56_shifts(db):
    """Feb 2026 has 28 days → 28 Kakad + 28 Robe = 56 shifts."""
    count = seed_month(db, 2026, 2)
    assert count == 56

    shifts = get_shifts_by_month(db, 2026, 2)
    assert len(shifts) == 56


def test_seed_is_idempotent(db):
    """Calling seed_month twice returns 0 the second time and doesn't duplicate."""
    first = seed_month(db, 2026, 2)
    assert first == 56

    second = seed_month(db, 2026, 2)
    assert second == 0

    shifts = get_shifts_by_month(db, 2026, 2)
    assert len(shifts) == 56


def test_every_day_has_kakad_and_robe(db):
    """Each day in the month must have exactly 1 Kakad and 1 Robe shift."""
    seed_month(db, 2026, 2)
    shifts = get_shifts_by_month(db, 2026, 2)

    by_date: dict[date, list] = {}
    for s in shifts:
        by_date.setdefault(s.date, []).append(s)

    assert len(by_date) == 28  # 28 days in Feb 2026

    for d, day_shifts in by_date.items():
        types = sorted(s.type for s in day_shifts)
        assert types == ["kakad", "robe"], f"Day {d} has types {types}"


def test_all_kakad_capacity_is_1(db):
    """Every Kakad shift must have capacity=1."""
    seed_month(db, 2026, 2)
    shifts = get_shifts_by_month(db, 2026, 2)

    kakad_shifts = [s for s in shifts if s.type == "kakad"]
    assert len(kakad_shifts) == 28

    for s in kakad_shifts:
        assert s.capacity == 1, f"Kakad on {s.date} has capacity {s.capacity}"


def test_robe_capacity_matches_day_of_week(db):
    """Robe capacity must follow get_robe_capacity for each day's weekday."""
    seed_month(db, 2026, 2)
    shifts = get_shifts_by_month(db, 2026, 2)

    robe_shifts = [s for s in shifts if s.type == "robe"]
    assert len(robe_shifts) == 28

    for s in robe_shifts:
        expected = get_robe_capacity(s.date.weekday())
        assert s.capacity == expected, (
            f"Robe on {s.date} (weekday={s.date.weekday()}) "
            f"has capacity {s.capacity}, expected {expected}"
        )
