import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.core.config import Settings

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"
MAX_BACKUPS_TO_KEEP = 10
_BACKUP_FILE_PATTERN = "weekly-report-*.db"


def run_startup_migrations(settings: Settings) -> None:
    """Applies pending Alembic migrations at startup.

    No-ops if the database is already at head. If the database file already
    has data, backs it up first (WAL checkpoint + `sqlite3` backup API) —
    per database.md section 5, migration only proceeds after a successful
    backup. Any failure here (backup or migration) propagates to the
    caller and must stop startup; this function never swallows exceptions.
    """
    is_existing_database = settings.database_path.exists()
    alembic_config = _build_alembic_config(settings)
    head_revision = ScriptDirectory.from_config(alembic_config).get_current_head()
    current_revision = _get_current_revision(settings) if is_existing_database else None

    if current_revision == head_revision:
        return

    if is_existing_database:
        _backup_database(settings)

    command.upgrade(alembic_config, "head")


def _build_alembic_config(settings: Settings) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.attributes["sqlalchemy_url"] = f"sqlite+aiosqlite:///{settings.database_path}"
    return config


def _get_current_revision(settings: Settings) -> str | None:
    # A separate plain-sync engine, deliberately not going through env.py:
    # this is a read-only inspection of the alembic_version table, not a
    # migration run.
    sync_engine = sqlalchemy.create_engine(f"sqlite:///{settings.database_path}")
    try:
        with sync_engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        sync_engine.dispose()


def _backup_database(settings: Settings) -> None:
    _checkpoint_wal(settings.database_path)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_path = settings.backup_dir / f"weekly-report-{timestamp}.db"
    _assert_within_directory(backup_path, settings.backup_dir)

    source = sqlite3.connect(settings.database_path)
    try:
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()

    _rotate_backups(settings.backup_dir)


def _checkpoint_wal(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        connection.close()


def _assert_within_directory(path: Path, directory: Path) -> None:
    resolved_directory = directory.resolve()
    if path.resolve().parent != resolved_directory:
        raise ValueError(f"refusing to write outside of {resolved_directory}: {path}")


def _rotate_backups(backup_dir: Path) -> None:
    backups = sorted(backup_dir.glob(_BACKUP_FILE_PATTERN))
    excess_count = len(backups) - MAX_BACKUPS_TO_KEEP
    for stale_backup in backups[: max(excess_count, 0)]:
        _assert_within_directory(stale_backup, backup_dir)
        stale_backup.unlink()
