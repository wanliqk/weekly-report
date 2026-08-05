"""Injectable UTC clock (coding-rule.md 4.3: no direct local-time calls).

Services take a `Clock` with this default so tests can substitute a fixed
or controlled time source instead of monkeypatching `datetime`.
"""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_naive_utc(value: datetime) -> datetime:
    """Strips tzinfo so a `Clock` value can compare against a SQLite column.

    SQLite round-trips `DateTime()` columns as naive (the numeric UTC
    wall-clock value survives; only `tzinfo` is lost), while every `Clock`
    returns UTC-aware values. Comparing them directly raises `TypeError`, so
    business logic that compares a freshly read column against `clock()`
    must go through this first.
    """
    return value.replace(tzinfo=None) if value.tzinfo is not None else value
