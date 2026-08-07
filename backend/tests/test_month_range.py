from datetime import date

import pytest

from app.core.month_range import InvalidMonthError, parse_month_range


def test_parses_a_regular_month() -> None:
    assert parse_month_range("2026-08") == (date(2026, 8, 1), date(2026, 8, 31))


def test_parses_december_by_rolling_into_next_year() -> None:
    assert parse_month_range("2026-12") == (date(2026, 12, 1), date(2026, 12, 31))


def test_parses_february_of_a_leap_year() -> None:
    assert parse_month_range("2024-02") == (date(2024, 2, 1), date(2024, 2, 29))


@pytest.mark.parametrize(
    "month",
    [
        "2026-13",
        "2026-00",
        "not-a-month",
        "2026-8-1",
        "2026",
        "",
    ],
)
def test_rejects_malformed_or_out_of_range_input(month: str) -> None:
    with pytest.raises(InvalidMonthError):
        parse_month_range(month)


def test_rejects_december_of_the_maximum_supported_year_instead_of_raising_unhandled() -> None:
    """Regression: `next_month_start` used to be computed outside the

    `try`/`except`, so `date.MAXYEAR`'s December rolled into year 10000 and
    raised an uncaught `ValueError` (500) instead of the intended `40001`.
    """
    with pytest.raises(InvalidMonthError):
        parse_month_range(f"{date.max.year}-12")
