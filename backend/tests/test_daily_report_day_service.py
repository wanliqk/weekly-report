from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.clock import as_naive_utc
from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import DailyReport, DailyReportDay, User
from app.services.bootstrap import BootstrapService
from app.services.daily_report import DailyReportService
from app.services.daily_report_day import (
    DailyReportDayArchiveNotConfirmedError,
    DailyReportDayHasDraftsError,
    DailyReportDayNothingToArchiveError,
    DailyReportDayService,
)
from app.services.template import parse_template_fields


@pytest.fixture
def day_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def day_engine(day_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(day_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _bootstrap_user(session_factory: object) -> User:
    async with session_factory() as session:  # type: ignore[operator]
        return await BootstrapService(session).bootstrap(
            username="owner", password=STAGE5_PASSWORD, display_name="Owner"
        )


async def _create_draft(session_factory: object, *, owner_id: str, work_date: date) -> DailyReport:
    async with session_factory() as session:  # type: ignore[operator]
        report, _created = await DailyReportService(session).create(
            owner_id, work_date=work_date, client_request_id=generate_ulid()
        )
        return report


async def _submit(session_factory: object, *, owner_id: str, report: DailyReport) -> DailyReport:
    async with session_factory() as session:  # type: ignore[operator]
        fields = parse_template_fields(report.template_snapshot_json)
        content: dict[str, object] = {
            field.field_key: f"{field.label}内容" for field in fields if field.required
        }
        saved = await DailyReportService(session).save(
            owner_id, report.id, expected_version=report.version, content=content
        )
        return await DailyReportService(session).submit(
            owner_id, report.id, expected_version=saved.version
        )


async def test_archive_requires_explicit_confirmation(day_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)
    async with session_factory() as session:
        with pytest.raises(DailyReportDayArchiveNotConfirmedError):
            await DailyReportDayService(session).archive(
                user.id, date(2026, 8, 5), confirm_archive=False
            )


async def test_archive_blocks_when_a_draft_still_exists(day_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    submitted_entry = await _create_draft(session_factory, owner_id=user.id, work_date=work_date)
    await _submit(session_factory, owner_id=user.id, report=submitted_entry)
    await _create_draft(session_factory, owner_id=user.id, work_date=work_date)

    async with session_factory() as session:
        with pytest.raises(DailyReportDayHasDraftsError):
            await DailyReportDayService(session).archive(user.id, work_date, confirm_archive=True)


async def test_archive_blocks_when_nothing_is_submitted(day_engine: AsyncEngine) -> None:
    """An open day with zero entries can't normally exist (`DailyReportService`
    always creates the day and its first entry together, and deleting the
    last draft removes the empty day with it — see `database.md` §8.4), but
    `40907` is still a documented contract error (`api.md` §13.5) that the
    Service must defend against defensively. Build the otherwise-unreachable
    state directly at the ORM layer to exercise that guard.
    """
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    async with session_factory() as session:
        session.add(
            DailyReportDay(
                id=generate_ulid(),
                user_id=user.id,
                work_date=work_date,
                status="open",
                source_count=0,
                version=1,
            )
        )
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(DailyReportDayNothingToArchiveError):
            await DailyReportDayService(session).archive(user.id, work_date, confirm_archive=True)


async def test_archive_aggregates_every_submitted_entry_into_one_snapshot(
    day_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    entries = [
        await _create_draft(session_factory, owner_id=user.id, work_date=work_date)
        for _ in range(3)
    ]
    submitted_ids = set[str]()
    for entry in entries:
        submitted = await _submit(session_factory, owner_id=user.id, report=entry)
        submitted_ids.add(submitted.id)

    async with session_factory() as session:
        day = await DailyReportDayService(session).archive(user.id, work_date, confirm_archive=True)

    assert day.status == "archived"
    assert day.source_count == 3
    assert day.archived_by == user.id
    async with session_factory() as session:
        detail = await DailyReportDayService(session).get_detail(user.id, work_date)
    assert detail.archive_snapshot is not None
    assert {entry.daily_report_id for entry in detail.archive_snapshot.entries} == submitted_ids
    assert all(entry.status == "archived" for entry in detail.entries)
    # Snapshot entries must be ordered by submitted_at ASC, id ASC (database.md §8.2).
    submitted_ats = [entry.submitted_at for entry in detail.archive_snapshot.entries]
    assert submitted_ats == sorted(submitted_ats)


async def test_archive_is_idempotent_when_called_again(day_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    entry = await _create_draft(session_factory, owner_id=user.id, work_date=work_date)
    await _submit(session_factory, owner_id=user.id, report=entry)

    async with session_factory() as session:
        first = await DailyReportDayService(session).archive(
            user.id, work_date, confirm_archive=True
        )
    async with session_factory() as session:
        second = await DailyReportDayService(session).archive(
            user.id, work_date, confirm_archive=True
        )

    assert first.archived_at is not None
    assert second.archived_at is not None
    assert as_naive_utc(first.archived_at) == as_naive_utc(second.archived_at)
    assert first.version == second.version


async def test_month_summary_reflects_every_day_state(day_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)

    draft_only = await _create_draft(session_factory, owner_id=user.id, work_date=date(2026, 8, 3))
    to_submit = await _create_draft(session_factory, owner_id=user.id, work_date=date(2026, 8, 4))
    await _submit(session_factory, owner_id=user.id, report=to_submit)
    to_archive = await _create_draft(session_factory, owner_id=user.id, work_date=date(2026, 8, 5))
    await _submit(session_factory, owner_id=user.id, report=to_archive)
    async with session_factory() as session:
        await DailyReportDayService(session).archive(
            user.id, date(2026, 8, 5), confirm_archive=True
        )

    async with session_factory() as session:
        items = await DailyReportDayService(session).month_summary(
            user.id, month_start=date(2026, 8, 1), month_end=date(2026, 8, 31)
        )
    by_date = {item.work_date: item for item in items}

    # Sparse by design (`docs/方案设计.md` §8.3): only dates with an actual
    # `daily_report_days` row are returned; 2026-08-01 never had a record.
    assert len(items) == 3
    assert date(2026, 8, 1) not in by_date
    assert by_date[date(2026, 8, 3)].status == "open"
    assert by_date[date(2026, 8, 3)].day_id == draft_only.day_id
    assert by_date[date(2026, 8, 3)].draft_count == 1
    assert by_date[date(2026, 8, 3)].can_archive is False
    assert by_date[date(2026, 8, 4)].submitted_count == 1
    assert by_date[date(2026, 8, 4)].can_archive is True
    assert by_date[date(2026, 8, 5)].status == "archived"
    assert by_date[date(2026, 8, 5)].can_create is False
    assert by_date[date(2026, 8, 5)].can_archive is False
    assert draft_only.status == "draft"


async def test_get_detail_for_a_date_with_no_entries_allows_creation(
    day_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(day_engine)
    user = await _bootstrap_user(session_factory)

    async with session_factory() as session:
        detail = await DailyReportDayService(session).get_detail(user.id, date(2026, 8, 9))

    assert detail.status == "open"
    assert detail.entries == []
    assert detail.archive_snapshot is None
    assert detail.can_archive is False
