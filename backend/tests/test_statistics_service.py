from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import User
from app.services.bootstrap import BootstrapService
from app.services.daily_report import DailyReportService
from app.services.daily_report_day import DailyReportDayService
from app.services.statistics import StatisticsService
from app.services.template import parse_template_fields
from app.services.user import UserService
from app.services.weekly_report import WeeklyReportService

_TODAY = date(2026, 8, 7)
_NOW = datetime(2026, 8, 7, 9, 0, 0, tzinfo=UTC)


def _clock() -> datetime:
    return _NOW


@pytest.fixture
def statistics_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def statistics_engine(statistics_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(statistics_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _bootstrap_user(session_factory: object) -> User:
    async with session_factory() as session:  # type: ignore[operator]
        return await BootstrapService(session).bootstrap(
            username="owner", password=STAGE5_PASSWORD, display_name="Owner"
        )


async def _archive_day(session_factory: object, *, owner_id: str, work_date: date) -> None:
    """Creates one entry, submits it with dummy content, and archives the day."""
    async with session_factory() as session:  # type: ignore[operator]
        report, _created = await DailyReportService(session, clock=_clock).create(
            owner_id, work_date=work_date, client_request_id=generate_ulid()
        )
        fields = parse_template_fields(report.template_snapshot_json)
        content: dict[str, object] = {
            field.field_key: f"{field.label}内容" for field in fields if field.required
        }
        saved = await DailyReportService(session, clock=_clock).save(
            owner_id, report.id, expected_version=report.version, content=content
        )
        await DailyReportService(session, clock=_clock).submit(
            owner_id, report.id, expected_version=saved.version
        )
    async with session_factory() as session:  # type: ignore[operator]
        await DailyReportDayService(session, clock=_clock).archive(
            owner_id, work_date, confirm_archive=True
        )


async def _create_draft(session_factory: object, *, owner_id: str, work_date: date) -> None:
    async with session_factory() as session:  # type: ignore[operator]
        await DailyReportService(session, clock=_clock).create(
            owner_id, work_date=work_date, client_request_id=generate_ulid()
        )


async def test_monthly_reflects_completed_days_and_daily_report_count(
    statistics_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(statistics_engine)
    user = await _bootstrap_user(session_factory)
    # Archived: two completed dates within the month, one of which is today.
    await _archive_day(session_factory, owner_id=user.id, work_date=date(2026, 8, 3))
    await _archive_day(session_factory, owner_id=user.id, work_date=_TODAY)
    # A draft (not submitted) must not count toward daily_report_count.
    await _create_draft(session_factory, owner_id=user.id, work_date=date(2026, 8, 6))

    async with session_factory() as session:
        result = await StatisticsService(session, clock=_clock).monthly(
            user.id, month="2026-08", month_start=date(2026, 8, 1), month_end=date(2026, 8, 31)
        )

    assert result.effective_date_from == date(2026, 8, 1)
    assert result.effective_date_to == _TODAY
    assert result.denominator_days == 7
    assert result.completed_days == 2
    assert result.completion_rate == round(2 / 7 * 100, 1)
    # Two archived entries (1 each) + zero from the untouched draft.
    assert result.daily_report_count == 2
    assert result.current_streak_days == 1
    by_date = {item.work_date: item for item in result.days}
    assert by_date[date(2026, 8, 3)].status == "archived"
    assert by_date[_TODAY].status == "archived"
    assert by_date[date(2026, 8, 6)].status == "open"


async def test_monthly_for_a_future_month_has_null_completion_rate(
    statistics_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(statistics_engine)
    user = await _bootstrap_user(session_factory)

    async with session_factory() as session:
        result = await StatisticsService(session, clock=_clock).monthly(
            user.id, month="2026-09", month_start=date(2026, 9, 1), month_end=date(2026, 9, 30)
        )

    assert result.denominator_days == 0
    assert result.completed_days == 0
    assert result.completion_rate is None


async def test_monthly_for_a_past_month_covers_the_whole_month(
    statistics_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(statistics_engine)
    user = await _bootstrap_user(session_factory)
    await _archive_day(session_factory, owner_id=user.id, work_date=date(2026, 7, 15))

    async with session_factory() as session:
        result = await StatisticsService(session, clock=_clock).monthly(
            user.id, month="2026-07", month_start=date(2026, 7, 1), month_end=date(2026, 7, 31)
        )

    assert result.effective_date_from == date(2026, 7, 1)
    assert result.effective_date_to == date(2026, 7, 31)
    assert result.denominator_days == 31
    assert result.completed_days == 1


async def test_monthly_weekly_report_count_uses_week_start_month(
    statistics_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(statistics_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        await WeeklyReportService(session, clock=_clock).generate(
            user.id, week_start=date(2026, 8, 3)
        )

    async with session_factory() as session:
        result = await StatisticsService(session, clock=_clock).monthly(
            user.id, month="2026-08", month_start=date(2026, 8, 1), month_end=date(2026, 8, 31)
        )

    assert result.weekly_report_count == 1


async def test_monthly_only_counts_the_current_users_own_records(
    statistics_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(statistics_engine)
    owner = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        other = await UserService(session, clock=_clock).create_user(
            username="other",
            password="another secure password",
            display_name="Other",
            role="user",
        )
    await _archive_day(session_factory, owner_id=other.id, work_date=_TODAY)

    async with session_factory() as session:
        result = await StatisticsService(session, clock=_clock).monthly(
            owner.id, month="2026-08", month_start=date(2026, 8, 1), month_end=date(2026, 8, 31)
        )

    assert result.completed_days == 0
    assert result.daily_report_count == 0
    assert result.days == []
