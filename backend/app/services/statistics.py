from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.timezone import to_shanghai
from app.repositories.daily_report import DailyReportRepository
from app.repositories.daily_report_day import DailyReportDayRepository
from app.repositories.weekly_report import WeeklyReportRepository
from app.services.daily_report_day import DailyReportDayService, DayMonthSummary


@dataclass(frozen=True)
class _EffectiveRange:
    date_from: date
    date_to: date
    denominator_days: int


def compute_effective_range(month_start: date, month_end: date, *, today: date) -> _EffectiveRange:
    """`docs/方案设计.md` §8.6: current month is partial (up to today),

    a fully past month is whole, and a fully future month has zero
    denominator — regardless of which case, `date_from` always stays
    `month_start` so the caller can render a stable "range so far" label.
    """
    if today < month_start:
        return _EffectiveRange(date_from=month_start, date_to=month_start, denominator_days=0)
    if today > month_end:
        return _EffectiveRange(
            date_from=month_start,
            date_to=month_end,
            denominator_days=(month_end - month_start).days + 1,
        )
    return _EffectiveRange(
        date_from=month_start, date_to=today, denominator_days=(today - month_start).days + 1
    )


def compute_completion_rate(completed_days: int, denominator_days: int) -> float | None:
    if denominator_days <= 0:
        return None
    return round(completed_days / denominator_days * 100, 1)


def compute_streak(archived_dates_desc: list[date], *, today: date) -> int:
    """Pure function implementing the today/yesterday streak rule

    (`docs/方案设计.md` §1 point 7): counts backward from today if today is
    archived, else from yesterday if yesterday is archived, else 0.
    """
    archived = set(archived_dates_desc)
    if today in archived:
        anchor = today
    elif (today - timedelta(days=1)) in archived:
        anchor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    current = anchor
    while current in archived:
        streak += 1
        current -= timedelta(days=1)
    return streak


@dataclass(frozen=True)
class StatisticsMonthly:
    month: str
    effective_date_from: date
    effective_date_to: date
    denominator_days: int
    completed_days: int
    completion_rate: float | None
    daily_report_count: int
    weekly_report_count: int
    current_streak_days: int
    days: list[DayMonthSummary]


class StatisticsService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._clock = clock
        self._daily_reports = DailyReportRepository(session)
        self._days = DailyReportDayRepository(session)
        self._weekly_reports = WeeklyReportRepository(session)
        self._day_service = DailyReportDayService(session, clock=clock)

    async def monthly(
        self, owner_id: str, *, month: str, month_start: date, month_end: date
    ) -> StatisticsMonthly:
        today = to_shanghai(self._clock()).date()
        effective = compute_effective_range(month_start, month_end, today=today)

        completed_days = 0
        if effective.denominator_days > 0:
            archived_days = await self._days.list_archived_in_range(
                owner_id, date_from=effective.date_from, date_to=effective.date_to
            )
            completed_days = len(archived_days)

        daily_report_count = await self._daily_reports.count_submitted_or_archived_in_range(
            owner_id, date_from=month_start, date_to=month_end
        )
        weekly_report_count = await self._weekly_reports.count_by_week_start_range(
            owner_id, date_from=month_start, date_to=month_end
        )
        archived_dates_desc = await self._days.list_archived_work_dates_on_or_before(
            owner_id, on_or_before=today
        )
        days = await self._day_service.month_summary(
            owner_id, month_start=month_start, month_end=month_end
        )

        return StatisticsMonthly(
            month=month,
            effective_date_from=effective.date_from,
            effective_date_to=effective.date_to,
            denominator_days=effective.denominator_days,
            completed_days=completed_days,
            completion_rate=compute_completion_rate(completed_days, effective.denominator_days),
            daily_report_count=daily_report_count,
            weekly_report_count=weekly_report_count,
            current_streak_days=compute_streak(archived_dates_desc, today=today),
            days=days,
        )
