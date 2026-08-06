from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.core.ulid import generate_ulid
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import (
    AdminAuditEvent,
    DailyReport,
    DailyReportDay,
    ReportTemplate,
    TemplateVersion,
    User,
)


@pytest.fixture
def migrated_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test", data_dir=tmp_path / "data", backup_dir=tmp_path / "backups"
    )
    ensure_runtime_directories(settings)
    # Sync, run from a sync fixture (no event loop yet): run_startup_migrations
    # itself drives Alembic via asyncio.run() and cannot be nested inside one.
    run_startup_migrations(settings)
    return settings


@pytest.fixture
async def session_factory(
    migrated_settings: Settings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(migrated_settings)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


def _new_user(**overrides: Any) -> User:
    defaults: dict[str, Any] = {
        "username": "alice",
        "username_normalized": "alice",
        "display_name": "Alice",
        "password_hash": "hash",
        "role": "user",
        "password_changed_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return User(**defaults)


async def test_unique_constraint_rejects_a_duplicate_normalized_username(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(_new_user(username_normalized="dup"))
        await session.commit()

    async with session_factory() as session:
        session.add(_new_user(username="Dup", username_normalized="dup"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_check_constraint_rejects_an_invalid_role(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(_new_user(role="superadmin"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_querying_by_user_id_only_returns_that_users_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user_a = _new_user(username="a", username_normalized="a")
        user_b = _new_user(username="b", username_normalized="b")
        session.add_all([user_a, user_b])
        await session.commit()

        rows = (await session.execute(select(User).where(User.id == user_a.id))).scalars().all()

    assert [row.id for row in rows] == [user_a.id]


async def test_optimistic_lock_update_affects_no_rows_on_a_stale_version(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        template = ReportTemplate(user_id=user.id, current_version_no=1)
        session.add(template)
        await session.flush()
        version = TemplateVersion(
            template_id=template.id, version_no=1, fields_json="[]", created_by=user.id
        )
        session.add(version)
        await session.flush()
        day = DailyReportDay(
            user_id=user.id,
            work_date=datetime.now(UTC).date(),
            status="open",
        )
        session.add(day)
        await session.flush()
        report_id = generate_ulid()
        report = DailyReport(
            id=report_id,
            day_id=day.id,
            client_request_id=report_id,
            status="draft",
            template_version_id=version.id,
            template_snapshot_json="[]",
            content_json="{}",
        )
        session.add(report)
        await session.commit()
        report_id = report.id

    async with session_factory() as session:
        # WHERE id=? AND version=? is the optimistic-lock pattern from
        # coding-rule.md 4.3; a stale version must affect zero rows.
        result = await session.execute(
            update(DailyReport)
            .where(DailyReport.id == report_id, DailyReport.version == 999)
            .values(content_json='{"x":1}')
        )
        await session.commit()

    assert result.rowcount == 0


async def test_daily_report_day_is_unique_per_owner_and_work_date(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        work_date = datetime.now(UTC).date()
        session.add(DailyReportDay(user_id=user.id, work_date=work_date, status="open"))
        await session.commit()

    async with session_factory() as session:
        session.add(DailyReportDay(user_id=user.id, work_date=work_date, status="open"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_archived_day_requires_a_complete_immutable_snapshot_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        session.add(
            DailyReportDay(
                user_id=user.id,
                work_date=datetime.now(UTC).date(),
                status="archived",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.parametrize(
    ("action", "reason"),
    [("unknown_action", "valid reason"), ("user_deleted", "   ")],
)
async def test_admin_audit_events_reject_unknown_actions_and_blank_reasons(
    session_factory: async_sessionmaker[AsyncSession],
    action: str,
    reason: str,
) -> None:
    async with session_factory() as session:
        admin = _new_user(role="admin")
        session.add(admin)
        await session.flush()
        session.add(
            AdminAuditEvent(
                action=action,
                actor_user_id=admin.id,
                actor_username_snapshot=admin.username,
                target_type="user",
                target_id="target",
                target_owner_id=None,
                reason=reason,
                metadata_json="{}",
                created_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_transaction_rollback_discards_all_changes_on_failure(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        session.add(_new_user(username_normalized="rollback-me"))
        await session.flush()
        session.add(_new_user(username="other", username_normalized="rollback-me"))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async with session_factory() as session:
        rows = (
            (await session.execute(select(User).where(User.username_normalized == "rollback-me")))
            .scalars()
            .all()
        )

    assert rows == []
