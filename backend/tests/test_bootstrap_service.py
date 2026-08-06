import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.security import verify_password
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import ReportTemplate, TemplateVersion, User, UserSettings
from app.services.bootstrap import (
    AlreadyInitializedError,
    BootstrapService,
    ReservedBootstrapUsernameError,
)

PASSWORD = "correct horse battery staple"


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


async def _count(session_factory: async_sessionmaker[AsyncSession], model: type) -> int:
    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(model))
        return result.scalar_one()


async def _all_users(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[User]:
    async with session_factory() as session:
        result = await session.execute(select(User).order_by(User.username))
        return list(result.scalars())


async def test_is_initialized_is_false_before_any_bootstrap(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        assert await BootstrapService(session).is_initialized() is False


async def test_bootstrap_atomically_creates_user_admin_and_both_default_resources(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        first_user = await BootstrapService(session).bootstrap(
            username="alice", password=PASSWORD, display_name="Alice"
        )

    users = await _all_users(session_factory)
    assert [user.username for user in users] == ["admin", "alice"]
    admin = users[0]
    assert first_user.role == "user"
    assert first_user.must_change_password is False
    assert admin.role == "admin"
    assert admin.display_name == "系统管理员"
    assert admin.must_change_password is True
    assert first_user.is_active is True
    assert admin.is_active is True
    assert verify_password(password=PASSWORD, password_hash=first_user.password_hash)
    assert verify_password(password=PASSWORD, password_hash=admin.password_hash)
    assert first_user.password_hash != admin.password_hash

    assert await _count(session_factory, UserSettings) == 2
    assert await _count(session_factory, ReportTemplate) == 2
    assert await _count(session_factory, TemplateVersion) == 2

    async with session_factory() as session:
        templates = list((await session.execute(select(ReportTemplate))).scalars())
        for template in templates:
            version = (
                await session.execute(
                    select(TemplateVersion).where(TemplateVersion.template_id == template.id)
                )
            ).scalar_one()
            assert version.created_by == template.user_id
            fields = json.loads(version.fields_json)
            assert [field["core_type"] for field in fields] == [
                "today_work",
                "tomorrow_plan",
            ]
            assert len({field["field_key"] for field in fields}) == 2


async def test_is_initialized_is_true_after_a_successful_bootstrap(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await BootstrapService(session).bootstrap(
            username="alice", password=PASSWORD, display_name="Alice"
        )

    async with session_factory() as session:
        assert await BootstrapService(session).is_initialized() is True


async def test_bootstrapping_twice_sequentially_rejects_the_second_attempt(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await BootstrapService(session).bootstrap(
            username="alice", password=PASSWORD, display_name="Alice"
        )

    async with session_factory() as session:
        with pytest.raises(AlreadyInitializedError) as excinfo:
            await BootstrapService(session).bootstrap(
                username="someone-else", password="another good password", display_name="Someone"
            )

    assert excinfo.value.code == 40001
    assert await _count(session_factory, User) == 2
    assert await _count(session_factory, UserSettings) == 2
    assert await _count(session_factory, ReportTemplate) == 2
    assert await _count(session_factory, TemplateVersion) == 2


async def test_concurrent_bootstrap_attempts_only_create_one_account_pair(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def _attempt(username: str) -> User | AlreadyInitializedError:
        async with session_factory() as session:
            try:
                return await BootstrapService(session).bootstrap(
                    username=username, password=PASSWORD, display_name="First User"
                )
            except AlreadyInitializedError as error:
                return error

    results = await asyncio.gather(_attempt("alice"), _attempt("bob"))

    assert len([result for result in results if isinstance(result, User)]) == 1
    assert len([result for result in results if isinstance(result, AlreadyInitializedError)]) == 1
    assert await _count(session_factory, User) == 2
    assert await _count(session_factory, UserSettings) == 2
    assert await _count(session_factory, ReportTemplate) == 2
    assert await _count(session_factory, TemplateVersion) == 2


async def test_bootstrap_rejects_the_reserved_admin_username_before_writing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        with pytest.raises(ReservedBootstrapUsernameError):
            await BootstrapService(session).bootstrap(
                username=" ADMIN ", password=PASSWORD, display_name="Not Allowed"
            )

    assert await _count(session_factory, User) == 0


async def test_bootstrap_uses_the_same_clock_for_both_accounts(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=UTC)

    async with session_factory() as session:
        await BootstrapService(session, clock=lambda: fixed_time).bootstrap(
            username="alice", password=PASSWORD, display_name="Alice"
        )

    users = await _all_users(session_factory)
    assert all(
        user.password_changed_at.replace(tzinfo=None) == fixed_time.replace(tzinfo=None)
        for user in users
    )


async def test_bootstrap_rolls_back_both_accounts_when_default_resource_creation_fails(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        with (
            patch(
                "app.services.bootstrap.create_default_user_resources",
                side_effect=RuntimeError("resource failure"),
            ),
            pytest.raises(RuntimeError, match="resource failure"),
        ):
            await BootstrapService(session).bootstrap(
                username="alice", password=PASSWORD, display_name="Alice"
            )
        await session.rollback()

    assert await _count(session_factory, User) == 0
    assert await _count(session_factory, UserSettings) == 0
