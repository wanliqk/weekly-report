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
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import DailyReport
from app.services.bootstrap import BootstrapService
from app.services.daily_report import DailyReportAlreadyExistsError, DailyReportService


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


async def test_concurrent_same_day_creation_produces_one_report(
    daily_engine: AsyncEngine,
) -> None:
    session_factory = create_session_factory(daily_engine)
    async with session_factory() as session:
        user = await BootstrapService(session).bootstrap_admin(
            username="admin", password=STAGE5_PASSWORD, display_name="Admin"
        )

    async def _create() -> DailyReport | DailyReportAlreadyExistsError:
        async with session_factory() as session:
            try:
                return await DailyReportService(session).create(user.id, work_date=date(2026, 8, 5))
            except DailyReportAlreadyExistsError as error:
                return error

    results = await asyncio.gather(_create(), _create())

    assert len([result for result in results if isinstance(result, DailyReport)]) == 1
    assert (
        len([result for result in results if isinstance(result, DailyReportAlreadyExistsError)])
        == 1
    )
    async with session_factory() as session:
        count = await session.execute(select(func.count()).select_from(DailyReport))
        assert count.scalar_one() == 1
