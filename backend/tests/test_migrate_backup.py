import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import (
    MAX_BACKUPS_TO_KEEP,
    _assert_within_directory,
    _rotate_backups,
    run_startup_migrations,
)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    settings = Settings(environment="test", data_dir=data_dir, backup_dir=backup_dir)
    ensure_runtime_directories(settings)
    return settings


def test_fresh_install_migrates_without_creating_any_backup(settings: Settings) -> None:
    run_startup_migrations(settings)

    assert settings.database_path.exists()
    assert list(settings.backup_dir.glob("*.db")) == []


def test_rerunning_on_an_up_to_date_database_is_a_no_op(settings: Settings) -> None:
    run_startup_migrations(settings)
    mtime_after_first_run = settings.database_path.stat().st_mtime

    run_startup_migrations(settings)

    assert settings.database_path.stat().st_mtime == mtime_after_first_run
    assert list(settings.backup_dir.glob("*.db")) == []


def test_an_existing_unstamped_database_is_backed_up_before_migrating(settings: Settings) -> None:
    # Simulate a pre-existing database file with no alembic_version table yet.
    sqlite3.connect(settings.database_path).close()

    run_startup_migrations(settings)

    backups = list(settings.backup_dir.glob("weekly-report-*.db"))
    assert len(backups) == 1
    # The backup must be a real, independently-openable sqlite snapshot.
    connection = sqlite3.connect(backups[0])
    try:
        table_count = connection.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert table_count == 0  # snapshot was taken of the pre-migration (empty) database


def test_migration_failure_propagates_and_is_not_swallowed(settings: Settings) -> None:
    with (
        patch("app.db.migrate.command.upgrade", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        run_startup_migrations(settings)


def test_backup_failure_stops_startup_before_any_migration_runs(settings: Settings) -> None:
    # Simulate a pre-existing, unstamped database so a backup is attempted.
    sqlite3.connect(settings.database_path).close()

    with (
        patch("app.db.migrate._checkpoint_wal", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        run_startup_migrations(settings)

    connection = sqlite3.connect(settings.database_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        connection.close()
    assert tables == set()  # migration must never have run


def test_rotate_backups_keeps_only_the_newest_max_backups(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for index in range(MAX_BACKUPS_TO_KEEP + 5):
        (backup_dir / f"weekly-report-2026010100000{index:02d}Z.db").touch()

    _rotate_backups(backup_dir)

    remaining = sorted(path.name for path in backup_dir.glob("weekly-report-*.db"))
    assert len(remaining) == MAX_BACKUPS_TO_KEEP
    # The oldest 5 (index 0-4) must be the ones removed.
    assert all(f"0000{index:02d}Z" not in "".join(remaining) for index in range(5))


def test_assert_within_directory_rejects_paths_outside_the_target_directory(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "backups"
    directory.mkdir()
    escaping_path = directory / ".." / "evil.db"

    with pytest.raises(ValueError, match="outside"):
        _assert_within_directory(escaping_path, directory)


def test_assert_within_directory_accepts_paths_inside_the_target_directory(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "backups"
    directory.mkdir()

    _assert_within_directory(directory / "weekly-report-x.db", directory)
