from datetime import UTC

from app.core.clock import utc_now


def test_utc_now_returns_a_timezone_aware_utc_datetime() -> None:
    value = utc_now()

    assert value.tzinfo is UTC
