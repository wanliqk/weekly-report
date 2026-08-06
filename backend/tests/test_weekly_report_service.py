import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import DailyReport, DailyReportDay, User, WeeklyReport, WeeklyReportSource
from app.repositories.daily_report import DailyReportRepository
from app.repositories.template import TemplateRepository
from app.services.bootstrap import BootstrapService
from app.services.weekly_report import (
    WeeklyRegenerateNotConfirmedError,
    WeeklyReportAlreadyExistsError,
    WeeklyReportNotFoundError,
    WeeklyReportService,
    WeeklyReportVersionConflictError,
    WeeklyWeekStartInvalidError,
)

_FIXED_NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def weekly_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def weekly_engine(weekly_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(weekly_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _default_template_version_id(session: AsyncSession, owner_id: str) -> str:
    repository = TemplateRepository(session)
    template = await repository.get_for_owner(owner_id)
    assert template is not None
    version = await repository.get_version(template.id, template.current_version_no)
    assert version is not None
    return version.id


async def _report(
    session: AsyncSession,
    *,
    owner_id: str,
    work_date: date,
    status: str,
    content: dict[str, str] | None = None,
) -> DailyReport:
    report_id = generate_ulid()
    is_archived = status == "archived"
    report = DailyReport(
        id=report_id,
        day_id=report_id,
        client_request_id=report_id,
        day=DailyReportDay(
            id=report_id,
            user_id=owner_id,
            work_date=work_date,
            status="archived" if is_archived else "open",
            archive_snapshot_json="{}" if is_archived else None,
            source_count=1 if is_archived else 0,
            archived_by=owner_id if is_archived else None,
            archived_at=_FIXED_NOW if is_archived else None,
        ),
        status=status,
        template_version_id=await _default_template_version_id(session, owner_id),
        template_snapshot_json="[]",
        content_json=json.dumps(content or {}, ensure_ascii=False),
        version=2 if status != "draft" else 1,
        submitted_at=_FIXED_NOW if status in {"submitted", "archived"} else None,
        archived_at=_FIXED_NOW if status == "archived" else None,
    )
    await DailyReportRepository(session).add(report)
    await session.commit()
    return report


async def _bootstrap_user(session: AsyncSession) -> User:
    return await BootstrapService(session).bootstrap(
        username="owner", password=STAGE5_PASSWORD, display_name="Owner"
    )


async def test_generate_only_counts_archived_reports_within_the_week(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 3), status="archived")
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 4), status="submitted")
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 5), status="draft")
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 10), status="archived")

    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    assert report.week_start == date(2026, 8, 3)
    assert report.week_end == date(2026, 8, 9)
    content = json.loads(report.content_json)
    assert [day["work_date"] for day in content["days"]] == ["2026-08-03"]

    async with session_factory() as session:
        sources = (
            (
                await session.execute(
                    select(WeeklyReportSource).where(
                        WeeklyReportSource.weekly_report_id == report.id
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(sources) == 1


async def test_generate_rejects_a_non_monday_week_start(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        with pytest.raises(WeeklyWeekStartInvalidError):
            await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 4))


async def test_generate_allows_an_empty_week(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    assert json.loads(report.content_json)["days"] == []


async def test_generate_rejects_duplicate_week_and_lists_existing_id(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        first = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    async with session_factory() as session:
        with pytest.raises(WeeklyReportAlreadyExistsError) as excinfo:
            await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    assert excinfo.value.data["existing_weekly_report_id"] == first.id


async def test_concurrent_generate_for_the_same_week_only_creates_one_report(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async def _generate() -> WeeklyReport | WeeklyReportAlreadyExistsError:
        async with session_factory() as session:
            try:
                return await WeeklyReportService(session).generate(
                    user.id, week_start=date(2026, 8, 3)
                )
            except WeeklyReportAlreadyExistsError as error:
                return error

    results = await asyncio.gather(_generate(), _generate())

    assert len([r for r in results if isinstance(r, WeeklyReport)]) == 1
    assert len([r for r in results if isinstance(r, WeeklyReportAlreadyExistsError)]) == 1


async def test_generate_handles_a_cross_year_week(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _report(session, owner_id=user.id, work_date=date(2025, 12, 31), status="archived")
        await _report(session, owner_id=user.id, work_date=date(2026, 1, 2), status="archived")

    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2025, 12, 29))

    assert report.week_end == date(2026, 1, 4)
    content = json.loads(report.content_json)
    assert [day["work_date"] for day in content["days"]] == ["2025-12-31", "2026-01-02"]


async def test_generate_handles_a_leap_day(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _report(session, owner_id=user.id, work_date=date(2024, 2, 29), status="archived")

    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2024, 2, 26))

    assert report.week_end == date(2024, 3, 3)
    content = json.loads(report.content_json)
    assert [day["work_date"] for day in content["days"]] == ["2024-02-29"]


async def test_availability_reports_status_per_day_and_existing_report(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 3), status="archived")
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 4), status="submitted")

    async with session_factory() as session:
        before = await WeeklyReportService(session).availability(user.id, date(2026, 8, 3))

    assert before.archived_count == 1
    assert before.non_archived_dates == [date(2026, 8, 4)]
    assert before.existing_weekly_report_id is None
    statuses = {day.work_date: day.status for day in before.days}
    assert statuses[date(2026, 8, 3)] == "archived"
    assert statuses[date(2026, 8, 4)] == "submitted"
    assert statuses[date(2026, 8, 5)] is None

    async with session_factory() as session:
        generated = await WeeklyReportService(session).generate(
            user.id, week_start=date(2026, 8, 3)
        )
    async with session_factory() as session:
        after = await WeeklyReportService(session).availability(user.id, date(2026, 8, 3))
    assert after.existing_weekly_report_id == generated.id


async def test_save_updates_free_text_without_touching_days_and_bumps_version(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 3), status="archived")
    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    async with session_factory() as session:
        saved = await WeeklyReportService(session).save(
            user.id,
            report.id,
            expected_version=report.version,
            supplement="补充",
            next_week_plan="计划",
            risks="风险",
        )

    assert saved.version == report.version + 1
    saved_content = json.loads(saved.content_json)
    original_content = json.loads(report.content_json)
    assert saved_content["days"] == original_content["days"]
    assert saved_content["supplement"] == "补充"
    assert saved_content["next_week_plan"] == "计划"
    assert saved_content["risks"] == "风险"
    # the auto-generated baseline is untouched by manual edits
    assert json.loads(saved.generated_content_json)["supplement"] == ""


async def test_save_with_stale_version_is_rejected(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    async with session_factory() as session:
        with pytest.raises(WeeklyReportVersionConflictError):
            await WeeklyReportService(session).save(
                user.id,
                report.id,
                expected_version=report.version + 1,
                supplement="x",
                next_week_plan="",
                risks="",
            )


async def test_regenerate_requires_explicit_confirmation(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    async with session_factory() as session:
        with pytest.raises(WeeklyRegenerateNotConfirmedError):
            await WeeklyReportService(session).regenerate(
                user.id, report.id, expected_version=report.version, confirm_overwrite=False
            )


async def test_regenerate_overwrites_both_generated_and_manual_content(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 3), status="archived")
    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))
    async with session_factory() as session:
        edited = await WeeklyReportService(session).save(
            user.id,
            report.id,
            expected_version=report.version,
            supplement="人工补充",
            next_week_plan="",
            risks="",
        )

    async with session_factory() as session:
        await _report(session, owner_id=user.id, work_date=date(2026, 8, 5), status="archived")
    async with session_factory() as session:
        regenerated = await WeeklyReportService(session).regenerate(
            user.id, edited.id, expected_version=edited.version, confirm_overwrite=True
        )

    assert regenerated.version == edited.version + 1
    new_content = json.loads(regenerated.content_json)
    assert new_content["supplement"] == ""
    assert [day["work_date"] for day in new_content["days"]] == ["2026-08-03", "2026-08-05"]
    assert json.loads(regenerated.generated_content_json) == new_content


async def test_regenerate_with_stale_version_is_rejected(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)
    async with session_factory() as session:
        report = await WeeklyReportService(session).generate(user.id, week_start=date(2026, 8, 3))

    async with session_factory() as session:
        with pytest.raises(WeeklyReportVersionConflictError):
            await WeeklyReportService(session).regenerate(
                user.id,
                report.id,
                expected_version=report.version + 1,
                confirm_overwrite=True,
            )


async def test_get_for_unknown_or_foreign_report_raises_not_found(
    weekly_engine: AsyncEngine, weekly_settings: Settings
) -> None:
    session_factory = create_session_factory(weekly_engine)
    async with session_factory() as session:
        user = await _bootstrap_user(session)

    async with session_factory() as session:
        with pytest.raises(WeeklyReportNotFoundError):
            await WeeklyReportService(session).get(user.id, "01MISSINGMISSINGMISSINGMI")
