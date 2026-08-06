import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

import app.services.backup as backup_service
from app.core.backup_registry import BackupRegistry
from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import run_startup_migrations
from app.services.backup import (
    BACKUP_MEDIA_TYPE,
    BackupCreationFailedError,
    BackupNotFoundError,
    BackupService,
    cleanup_stale_manual_backups,
)


def _past_clock() -> datetime:
    """Far enough in the past that `expires_at` (+15min) is already behind
    any real wall-clock `now`, regardless of when tests run."""
    return datetime(2000, 1, 1, tzinfo=UTC)


@pytest.fixture
def backup_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        manual_backup_temp_dir=tmp_path / "manual-backups",
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
def registry() -> BackupRegistry:
    return BackupRegistry()


async def test_create_produces_a_valid_sqlite_snapshot_owned_by_the_requesting_admin(
    backup_settings: Settings, registry: BackupRegistry
) -> None:
    record = await BackupService(registry, backup_settings).create("admin-1")

    assert record.owner_id == "admin-1"
    assert record.file_name.startswith("weekly-report-backup-")
    assert record.file_name.endswith(".db")
    assert record.path.parent == backup_settings.manual_backup_temp_dir.resolve()
    assert record.path.exists()

    connection = sqlite3.connect(record.path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        connection.close()
    assert "users" in tables
    assert "daily_reports" in tables


async def test_get_download_rejects_a_different_admin(
    backup_settings: Settings, registry: BackupRegistry
) -> None:
    record = await BackupService(registry, backup_settings).create("admin-1")

    with pytest.raises(BackupNotFoundError):
        await BackupService(registry, backup_settings).get_download("admin-2", record.id)


async def test_get_download_expires_lazily_and_deletes_the_file(
    backup_settings: Settings, registry: BackupRegistry
) -> None:
    record = await BackupService(registry, backup_settings, clock=_past_clock).create("admin-1")
    assert record.path.exists()

    with pytest.raises(BackupNotFoundError):
        await BackupService(registry, backup_settings).get_download("admin-1", record.id)

    assert not record.path.exists()
    assert registry.get(record.id) is None


async def test_get_download_rejects_unknown_backup_id(
    backup_settings: Settings, registry: BackupRegistry
) -> None:
    with pytest.raises(BackupNotFoundError):
        await BackupService(registry, backup_settings).get_download(
            "admin-1", "01MISSINGMISSINGMISSINGMI"
        )


async def test_get_download_rejects_files_outside_the_backup_directory(
    backup_settings: Settings, registry: BackupRegistry, tmp_path: Path
) -> None:
    outside_file = tmp_path / "outside.db"
    outside_file.write_bytes(b"not a real backup")
    record = await BackupService(registry, backup_settings).create("admin-1")
    record.path.unlink()
    record.path = outside_file

    with pytest.raises(BackupNotFoundError):
        await BackupService(registry, backup_settings).get_download("admin-1", record.id)
    assert outside_file.exists()


async def test_create_prunes_previously_expired_backups_from_the_registry(
    backup_settings: Settings, registry: BackupRegistry
) -> None:
    stale = await BackupService(registry, backup_settings, clock=_past_clock).create("admin-1")
    assert stale.path.exists()

    await BackupService(registry, backup_settings).create("admin-1")

    assert registry.get(stale.id) is None
    assert not stale.path.exists()


async def test_create_raises_typed_error_when_the_destination_directory_is_missing(
    backup_settings: Settings, registry: BackupRegistry
) -> None:
    broken_settings = backup_settings.model_copy(
        update={
            "manual_backup_temp_dir": backup_settings.manual_backup_temp_dir / "missing" / "nested"
        }
    )

    with pytest.raises(BackupCreationFailedError):
        await BackupService(registry, broken_settings).create("admin-1")

    assert registry.list_all() == []


async def test_create_removes_a_partially_written_file_when_the_backup_copy_fails(
    backup_settings: Settings, registry: BackupRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `sqlite3.Connection` is a C-level immutable type (its methods can't be
    # monkeypatched directly), so this simulates the real failure shape —
    # `_create_backup_file` gets partway through and leaves a truncated
    # destination file on disk before raising — by patching the module-level
    # helper `BackupService.create` calls, rather than sqlite3 internals.
    def _fake_create_backup_file(_database_path: Path, destination_path: Path) -> None:
        destination_path.write_bytes(b"partial write before a simulated disk-full error")
        raise sqlite3.OperationalError("simulated disk-full mid-copy")

    monkeypatch.setattr(backup_service, "_create_backup_file", _fake_create_backup_file)

    with pytest.raises(BackupCreationFailedError):
        await BackupService(registry, backup_settings).create("admin-1")

    assert list(backup_settings.manual_backup_temp_dir.glob("*.db")) == []
    assert registry.list_all() == []


def test_cleanup_stale_manual_backups_removes_leftover_files_from_a_previous_run(
    backup_settings: Settings,
) -> None:
    leftover = backup_settings.manual_backup_temp_dir / "01LEFTOVERLEFTOVERLEFTOVER.db"
    leftover.write_bytes(b"orphaned from a crashed previous run")

    cleanup_stale_manual_backups(backup_settings)

    assert not leftover.exists()


def test_backup_media_type_is_sqlite() -> None:
    assert BACKUP_MEDIA_TYPE == "application/vnd.sqlite3"
