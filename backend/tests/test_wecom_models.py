from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.engine import create_engine
from app.db.migrate import run_startup_migrations
from app.db.session import create_session_factory
from app.models import (
    DailyReportDay,
    User,
    WeComDailySyncRecord,
    WeComSyncProfile,
    WeComUserBinding,
)

FINGERPRINT_A = "a" * 64
FINGERPRINT_B = "b" * 64


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


def _new_binding(user_id: str, **overrides: Any) -> WeComUserBinding:
    defaults: dict[str, Any] = {
        "user_id": user_id,
        "credential_slot": "slot-" + user_id,
        "wecom_vid": "1000001",
        "display_name": "张三",
        "status": "connected",
    }
    defaults.update(overrides)
    return WeComUserBinding(**defaults)


def _new_profile(user_id: str, **overrides: Any) -> WeComSyncProfile:
    defaults: dict[str, Any] = {
        "user_id": user_id,
        "form_id": "form-1",
        "template_id": "template-1",
        "destination_fingerprint": FINGERPRINT_A,
        "question_mapping_json": '{"schema_version":1}',
        "recipient_config_json": '{"schema_version":1}',
        "field_mapping_json": '{"schema_version":1}',
        "schema_fingerprint": FINGERPRINT_B,
    }
    defaults.update(overrides)
    return WeComSyncProfile(**defaults)


def _new_day(user_id: str, **overrides: Any) -> DailyReportDay:
    defaults: dict[str, Any] = {
        "user_id": user_id,
        "work_date": date(2026, 8, 8),
        "status": "open",
    }
    defaults.update(overrides)
    return DailyReportDay(**defaults)


def _new_sync_record(
    *, user_id: str, day_id: str, profile_id: str, **overrides: Any
) -> WeComDailySyncRecord:
    defaults: dict[str, Any] = {
        "user_id": user_id,
        "daily_report_day_id": day_id,
        "profile_id": profile_id,
        "profile_version": 1,
        "destination_fingerprint": FINGERPRINT_A,
        "payload_fingerprint": FINGERPRINT_B,
        "status": "pending",
    }
    defaults.update(overrides)
    return WeComDailySyncRecord(**defaults)


async def test_user_binding_can_be_created_with_valid_data(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        binding = _new_binding(user.id)
        session.add(binding)
        await session.commit()

    assert binding.id
    assert binding.version == 1
    assert binding.corp_id is None


async def test_user_binding_is_unique_per_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        session.add(_new_binding(user.id))
        await session.commit()

    async with session_factory() as session:
        session.add(_new_binding(user.id, credential_slot="another-slot"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_user_binding_credential_slot_is_globally_unique(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user_a = _new_user(username="a", username_normalized="a")
        user_b = _new_user(username="b", username_normalized="b")
        session.add_all([user_a, user_b])
        await session.flush()
        session.add(_new_binding(user_a.id, credential_slot="shared-slot"))
        await session.commit()

    async with session_factory() as session:
        session.add(_new_binding(user_b.id, credential_slot="shared-slot"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_user_binding_rejects_an_invalid_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        session.add(_new_binding(user.id, status="revoked"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_sync_profile_can_be_created_with_valid_data(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        session.add(profile)
        await session.commit()

    assert profile.id
    assert profile.version == 1
    assert profile.is_active is True


async def test_sync_profile_is_unique_per_user(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        session.add(_new_profile(user.id))
        await session.commit()

    async with session_factory() as session:
        session.add(_new_profile(user.id, form_id="form-2"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_sync_profile_rejects_a_malformed_destination_fingerprint(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        session.add(_new_profile(user.id, destination_fingerprint="too-short"))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_daily_sync_record_can_be_created_with_valid_data(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        day = _new_day(user.id)
        session.add_all([profile, day])
        await session.flush()
        record = _new_sync_record(user_id=user.id, day_id=day.id, profile_id=profile.id)
        session.add(record)
        await session.commit()

    assert record.id
    assert record.attempt_count == 0
    assert record.last_error_kind is None


async def test_daily_sync_record_rejects_an_invalid_status(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        day = _new_day(user.id)
        session.add_all([profile, day])
        await session.flush()
        session.add(
            _new_sync_record(
                user_id=user.id, day_id=day.id, profile_id=profile.id, status="cancelled"
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_daily_sync_record_is_unique_per_day_and_destination(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        day = _new_day(user.id)
        session.add_all([profile, day])
        await session.flush()
        session.add(_new_sync_record(user_id=user.id, day_id=day.id, profile_id=profile.id))
        await session.commit()

    async with session_factory() as session:
        # Same day + same destination fingerprint must be rejected...
        session.add(_new_sync_record(user_id=user.id, day_id=day.id, profile_id=profile.id))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_daily_sync_record_allows_a_second_row_for_a_different_destination(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        day = _new_day(user.id)
        session.add_all([profile, day])
        await session.flush()
        session.add(_new_sync_record(user_id=user.id, day_id=day.id, profile_id=profile.id))
        await session.commit()

    async with session_factory() as session:
        # ...but switching to a different target destination is a new row.
        session.add(
            _new_sync_record(
                user_id=user.id,
                day_id=day.id,
                profile_id=profile.id,
                destination_fingerprint=FINGERPRINT_B,
            )
        )
        await session.commit()


async def test_daily_sync_record_rejects_a_negative_attempt_count(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        day = _new_day(user.id)
        session.add_all([profile, day])
        await session.flush()
        session.add(
            _new_sync_record(
                user_id=user.id, day_id=day.id, profile_id=profile.id, attempt_count=-1
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_daily_sync_record_rejects_a_blank_last_error_message(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        day = _new_day(user.id)
        session.add_all([profile, day])
        await session.flush()
        session.add(
            _new_sync_record(
                user_id=user.id,
                day_id=day.id,
                profile_id=profile.id,
                last_error_message="   ",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_daily_sync_record_rejects_an_unknown_daily_report_day(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        user = _new_user()
        session.add(user)
        await session.flush()
        profile = _new_profile(user.id)
        session.add(profile)
        await session.flush()
        session.add(_new_sync_record(user_id=user.id, day_id="missing-day", profile_id=profile.id))
        with pytest.raises(IntegrityError):
            await session.commit()
