import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

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
from app.services.bootstrap import AlreadyInitializedError, BootstrapService


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


async def test_is_initialized_is_false_before_any_bootstrap(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        assert await BootstrapService(session).is_initialized() is False


async def test_bootstrap_admin_atomically_creates_admin_settings_template_and_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = await BootstrapService(session).bootstrap_admin(
            username="admin", password="correct horse battery staple", display_name="Admin"
        )

    assert user.role == "admin"
    assert user.is_active is True
    assert user.token_version == 1
    assert user.username_normalized == "admin"
    assert verify_password(
        password="correct horse battery staple", password_hash=user.password_hash
    )

    async with session_factory() as session:
        assert await session.get(UserSettings, user.id) is not None

        template = (
            await session.execute(select(ReportTemplate).where(ReportTemplate.user_id == user.id))
        ).scalar_one()
        assert template.current_version_no == 1

        version = (
            await session.execute(
                select(TemplateVersion).where(TemplateVersion.template_id == template.id)
            )
        ).scalar_one()
        assert version.created_by == user.id
        fields = json.loads(version.fields_json)
        assert [field["core_type"] for field in fields] == ["today_work", "tomorrow_plan"]
        assert [field["label"] for field in fields] == ["今日工作内容", "明日工作计划"]
        assert all(field["required"] and field["enabled"] for field in fields)
        field_keys = {field["field_key"] for field in fields}
        assert len(field_keys) == 2  # stable, distinct field_key per field


async def test_is_initialized_is_true_after_a_successful_bootstrap(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await BootstrapService(session).bootstrap_admin(
            username="admin", password="correct horse battery staple", display_name="Admin"
        )

    async with session_factory() as session:
        assert await BootstrapService(session).is_initialized() is True


async def test_bootstrapping_twice_sequentially_rejects_the_second_attempt(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await BootstrapService(session).bootstrap_admin(
            username="admin", password="correct horse battery staple", display_name="Admin"
        )

    async with session_factory() as session:
        with pytest.raises(AlreadyInitializedError) as excinfo:
            await BootstrapService(session).bootstrap_admin(
                username="someone-else", password="another good password", display_name="Someone"
            )

    assert excinfo.value.code == 40001
    assert excinfo.value.http_status == 400
    assert await _count(session_factory, User) == 1
    assert await _count(session_factory, ReportTemplate) == 1
    assert await _count(session_factory, TemplateVersion) == 1


async def test_concurrent_bootstrap_attempts_only_ever_create_one_admin(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def _attempt(username: str) -> User | AlreadyInitializedError:
        async with session_factory() as session:
            try:
                return await BootstrapService(session).bootstrap_admin(
                    username=username, password="correct horse battery staple", display_name="A"
                )
            except AlreadyInitializedError as error:
                return error

    results = await asyncio.gather(_attempt("admin-one"), _attempt("admin-two"))

    successes = [result for result in results if isinstance(result, User)]
    failures = [result for result in results if isinstance(result, AlreadyInitializedError)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert await _count(session_factory, User) == 1
    assert await _count(session_factory, UserSettings) == 1
    assert await _count(session_factory, ReportTemplate) == 1
    assert await _count(session_factory, TemplateVersion) == 1


async def test_bootstrap_admin_sets_password_changed_at_via_the_clock(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=UTC)

    async with session_factory() as session:
        user = await BootstrapService(session, clock=lambda: fixed_time).bootstrap_admin(
            username="admin", password="correct horse battery staple", display_name="Admin"
        )

    # SQLite has no native timezone-aware storage; compare component-wise.
    assert user.password_changed_at.replace(tzinfo=None) == fixed_time.replace(tzinfo=None)
