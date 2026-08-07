from datetime import date

from app.services.statistics import (
    compute_completion_rate,
    compute_effective_range,
    compute_streak,
)


def test_effective_range_for_the_current_month_stops_at_today() -> None:
    result = compute_effective_range(date(2026, 8, 1), date(2026, 8, 31), today=date(2026, 8, 7))

    assert result.date_from == date(2026, 8, 1)
    assert result.date_to == date(2026, 8, 7)
    assert result.denominator_days == 7


def test_effective_range_for_a_historical_month_covers_the_whole_month() -> None:
    result = compute_effective_range(date(2026, 7, 1), date(2026, 7, 31), today=date(2026, 8, 7))

    assert result.date_from == date(2026, 7, 1)
    assert result.date_to == date(2026, 7, 31)
    assert result.denominator_days == 31


def test_effective_range_for_a_future_month_has_zero_denominator() -> None:
    result = compute_effective_range(date(2026, 9, 1), date(2026, 9, 30), today=date(2026, 8, 7))

    assert result.denominator_days == 0


def test_effective_range_handles_february_of_a_leap_year() -> None:
    result = compute_effective_range(date(2024, 2, 1), date(2024, 2, 29), today=date(2024, 3, 1))

    assert result.date_to == date(2024, 2, 29)
    assert result.denominator_days == 29


def test_effective_range_handles_february_of_a_non_leap_year() -> None:
    result = compute_effective_range(date(2026, 2, 1), date(2026, 2, 28), today=date(2026, 3, 1))

    assert result.denominator_days == 28


def test_completion_rate_matches_the_documented_example() -> None:
    assert compute_completion_rate(5, 7) == 71.4


def test_completion_rate_is_none_when_denominator_is_zero() -> None:
    assert compute_completion_rate(0, 0) is None


def test_completion_rate_rounds_to_one_decimal_place() -> None:
    assert compute_completion_rate(1, 3) == 33.3


def test_streak_counts_backward_from_today_when_today_is_archived() -> None:
    today = date(2026, 8, 7)
    archived = [today, today.replace(day=6), today.replace(day=5)]

    assert compute_streak(archived, today=today) == 3


def test_streak_matches_the_documented_yesterday_example() -> None:
    """requirements.md: today incomplete, yesterday and the day before both

    complete, the day before that incomplete -> streak of 2.
    """
    today = date(2026, 8, 7)
    archived = [date(2026, 8, 6), date(2026, 8, 5)]

    assert compute_streak(archived, today=today) == 2


def test_streak_is_zero_when_most_recent_completion_is_older_than_yesterday() -> None:
    today = date(2026, 8, 7)
    archived = [date(2026, 8, 4)]

    assert compute_streak(archived, today=today) == 0


def test_streak_is_zero_with_no_archived_dates() -> None:
    assert compute_streak([], today=date(2026, 8, 7)) == 0


def test_streak_stops_at_the_first_gap_going_backward() -> None:
    today = date(2026, 8, 7)
    archived = [today, today.replace(day=6), date(2026, 8, 4)]  # gap on the 5th

    assert compute_streak(archived, today=today) == 2


def test_streak_handles_a_run_crossing_a_year_boundary() -> None:
    today = date(2026, 1, 1)
    archived = [date(2026, 1, 1), date(2025, 12, 31), date(2025, 12, 30)]

    assert compute_streak(archived, today=today) == 3
