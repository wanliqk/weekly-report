import asyncio
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from conftest import STAGE5_PASSWORD
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import DailyReport, DailyReportDay, User
from app.services.bootstrap import BootstrapService
from app.services.daily_report import (
    DailyReportDayArchivedError,
    DailyReportIdempotencyConflictError,
    DailyReportService,
)
from app.services.daily_report_day import DailyReportDayHasDraftsError, DailyReportDayService
from app.services.template import parse_template_fields


@pytest.fixture
def daily_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def daily_engine(daily_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(daily_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _bootstrap_user(session_factory: object) -> User:
    async with session_factory() as session:  # type: ignore[operator]
        return await BootstrapService(session).bootstrap(
            username="owner", password=STAGE5_PASSWORD, display_name="Owner"
        )


async def _submit_full(session_factory: object, *, owner_id: str, report: DailyReport) -> None:
    """Fills every required field with dummy text and submits the entry."""
    async with session_factory() as session:  # type: ignore[operator]
        fields = parse_template_fields(report.template_snapshot_json)
        content: dict[str, object] = {
            field.field_key: f"{field.label}内容" for field in fields if field.required
        }
        saved = await DailyReportService(session).save(
            owner_id, report.id, expected_version=report.version, content=content
        )
        await DailyReportService(session).submit(
            owner_id, report.id, expected_version=saved.version
        )


async def test_concurrent_creation_with_distinct_keys_produces_two_entries(
    daily_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)

    async def _create(key: str) -> DailyReport:
        async with session_factory() as session:
            return await DailyReportService(session).create(
                user.id, work_date=date(2026, 8, 5), client_request_id=key
            )

    first, second = await asyncio.gather(_create(generate_ulid()), _create(generate_ulid()))

    assert first.id != second.id
    assert first.day_id == second.day_id
    async with session_factory() as session:
        entry_count = await session.execute(select(func.count()).select_from(DailyReport))
        assert entry_count.scalar_one() == 2
        day_count = await session.execute(select(func.count()).select_from(DailyReportDay))
        assert day_count.scalar_one() == 1


async def test_concurrent_creation_with_the_same_key_is_idempotent(
    daily_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)
    key = generate_ulid()

    async def _create() -> DailyReport:
        async with session_factory() as session:
            return await DailyReportService(session).create(
                user.id, work_date=date(2026, 8, 5), client_request_id=key
            )

    first, second = await asyncio.gather(_create(), _create())

    assert first.id == second.id
    async with session_factory() as session:
        count = await session.execute(select(func.count()).select_from(DailyReport))
        assert count.scalar_one() == 1


async def test_replaying_client_request_id_for_a_different_date_is_rejected(
    daily_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)
    key = generate_ulid()
    async with session_factory() as session:
        await DailyReportService(session).create(
            user.id, work_date=date(2026, 8, 5), client_request_id=key
        )

    async with session_factory() as session:
        with pytest.raises(DailyReportIdempotencyConflictError):
            await DailyReportService(session).create(
                user.id, work_date=date(2026, 8, 6), client_request_id=key
            )


async def test_create_is_rejected_once_the_day_is_archived(daily_engine: AsyncEngine) -> None:
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    async with session_factory() as session:
        report = await DailyReportService(session).create(
            user.id, work_date=work_date, client_request_id=generate_ulid()
        )
    await _submit_full(session_factory, owner_id=user.id, report=report)
    async with session_factory() as session:
        await DailyReportDayService(session).archive(user.id, work_date, confirm_archive=True)

    async with session_factory() as session:
        with pytest.raises(DailyReportDayArchivedError):
            await DailyReportService(session).create(
                user.id, work_date=work_date, client_request_id=generate_ulid()
            )


async def test_concurrent_create_and_archive_resolve_to_exactly_one_success(
    daily_engine: AsyncEngine,
) -> None:
    """Demonstrates the day-row mutex from `database.md` §8.2 (ADR-016).

    Whichever of {a new draft appearing, the day being archived} the other
    transaction observes first determines the outcome deterministically: a
    fresh draft blocks archival (40906), and an archived day blocks new
    entries (40905). Exactly one of the two operations can ever succeed.
    """
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    async with session_factory() as session:
        report = await DailyReportService(session).create(
            user.id, work_date=work_date, client_request_id=generate_ulid()
        )
    await _submit_full(session_factory, owner_id=user.id, report=report)

    async def _create_new_entry() -> DailyReport | Exception:
        async with session_factory() as session:
            try:
                return await DailyReportService(session).create(
                    user.id, work_date=work_date, client_request_id=generate_ulid()
                )
            except (DailyReportDayArchivedError, DailyReportDayHasDraftsError) as error:
                return error

    async def _archive_day() -> DailyReportDay | Exception:
        async with session_factory() as session:
            try:
                return await DailyReportDayService(session).archive(
                    user.id, work_date, confirm_archive=True
                )
            except DailyReportDayHasDraftsError as error:
                return error

    create_result, archive_result = await asyncio.gather(_create_new_entry(), _archive_day())

    create_ok = isinstance(create_result, DailyReport)
    archive_ok = isinstance(archive_result, DailyReportDay)
    assert create_ok != archive_ok, (create_result, archive_result)
    if create_ok:
        assert isinstance(archive_result, DailyReportDayHasDraftsError)
    else:
        assert isinstance(create_result, DailyReportDayArchivedError)


async def test_deleting_the_last_draft_removes_the_empty_open_day(
    daily_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    async with session_factory() as session:
        report = await DailyReportService(session).create(
            user.id, work_date=work_date, client_request_id=generate_ulid()
        )

    async with session_factory() as session:
        await DailyReportService(session).delete(
            user.id, report.id, expected_version=report.version
        )

    async with session_factory() as session:
        remaining_day = await DailyReportDayService(session).get_for_owner(user.id, work_date)
        assert remaining_day is None

    async with session_factory() as session:
        recreated = await DailyReportService(session).create(
            user.id, work_date=work_date, client_request_id=generate_ulid()
        )
        assert recreated.day_id != report.day_id


async def test_deleting_one_of_several_drafts_keeps_the_day_open(
    daily_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(daily_engine)
    user = await _bootstrap_user(session_factory)
    work_date = date(2026, 8, 5)
    async with session_factory() as session:
        first = await DailyReportService(session).create(
            user.id, work_date=work_date, client_request_id=generate_ulid()
        )
    async with session_factory() as session:
        second = await DailyReportService(session).create(
            user.id, work_date=work_date, client_request_id=generate_ulid()
        )

    async with session_factory() as session:
        await DailyReportService(session).delete(user.id, first.id, expected_version=first.version)

    async with session_factory() as session:
        day = await DailyReportDayService(session).get_for_owner(user.id, work_date)
        assert day is not None
        assert day.id == second.day_id
