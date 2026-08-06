import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import User
from app.services.bootstrap import BootstrapService
from app.services.user import LastActiveAdminError, UserService


@pytest.fixture
def migrated_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def engine(migrated_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(migrated_settings)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


async def test_concurrent_admin_disables_preserve_one_active_admin(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await BootstrapService(session).bootstrap(
            username="owner", password="first admin password", display_name="Owner"
        )
        first = (
            await session.execute(select(User).where(User.username_normalized == "admin"))
        ).scalar_one()
    async with session_factory() as session:
        second = await UserService(session).create_user(
            username="admin-two",
            password="second admin password",
            display_name="Admin Two",
            role="admin",
        )

    async def _disable(user_id: str) -> User | LastActiveAdminError:
        async with session_factory() as session:
            try:
                return await UserService(session).update_user(
                    user_id, display_name=None, role=None, is_active=False
                )
            except LastActiveAdminError as error:
                return error

    results = await asyncio.gather(_disable(first.id), _disable(second.id))

    assert len([result for result in results if isinstance(result, User)]) == 1
    assert len([result for result in results if isinstance(result, LastActiveAdminError)]) == 1
    async with session_factory() as session:
        active_admins = await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.is_active.is_(True))
        )
        assert active_admins.scalar_one() == 1
