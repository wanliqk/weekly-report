import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.core.backup_registry import BackupRecord, BackupRegistry
from app.core.clock import Clock, utc_now
from app.core.config import Settings
from app.core.errors import AppError
from app.core.timezone import to_shanghai
from app.core.ulid import generate_ulid

logger = logging.getLogger(__name__)

BACKUP_EXPIRY = timedelta(minutes=15)
BACKUP_MEDIA_TYPE = "application/vnd.sqlite3"

_BACKUP_FILE_GLOB = "*.db"


class BackupNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="备份不存在或已过期")


class BackupCreationFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(code=50001, http_status=500, message="备份创建失败")


def _backup_file_name(moment: datetime) -> str:
    timestamp = to_shanghai(moment).strftime("%Y%m%d-%H%M%S")
    return f"weekly-report-backup-{timestamp}.db"


def _create_backup_file(database_path: Path, destination_path: Path) -> None:
    """Blocking WAL-checkpoint + SQLite backup-API snapshot.

    Callers must run this off the event loop (`asyncio.to_thread`). Mirrors
    `db/migrate.py::_backup_database`'s sequence (database.md §5: checkpoint
    before the backup API), applied here on demand instead of only ahead of
    a migration.
    """
    source = sqlite3.connect(database_path)
    try:
        source.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        destination = sqlite3.connect(destination_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()


class BackupService:
    def __init__(
        self,
        registry: BackupRegistry,
        settings: Settings,
        *,
        clock: Clock = utc_now,
    ) -> None:
        self._registry = registry
        self._settings = settings
        self._clock = clock

    async def create(self, admin_user_id: str) -> BackupRecord:
        now = self._clock()
        self._prune_expired(now)
        backup_id = generate_ulid()
        destination_path = self._settings.manual_backup_temp_dir / f"{backup_id}.db"
        try:
            await asyncio.to_thread(
                _create_backup_file, self._settings.database_path, destination_path
            )
        except sqlite3.Error:
            logger.exception("manual backup creation failed")
            # sqlite3.Connection.backup() can fail partway through (e.g. disk
            # full), leaving a truncated destination file on disk; since this
            # path never reaches `self._registry.add`, nothing else would
            # ever clean it up before the next process restart's
            # `cleanup_stale_manual_backups` sweep.
            destination_path.unlink(missing_ok=True)
            raise BackupCreationFailedError() from None

        record = BackupRecord(
            id=backup_id,
            owner_id=admin_user_id,
            file_name=_backup_file_name(now),
            path=destination_path,
            created_at=now,
            expires_at=now + BACKUP_EXPIRY,
        )
        self._registry.add(record)
        return record

    async def get_download(self, admin_user_id: str, backup_id: str) -> tuple[str, Path]:
        record = self._registry.get(backup_id)
        if record is None or record.owner_id != admin_user_id:
            raise BackupNotFoundError()
        if record.expires_at <= self._clock():
            self._discard(record)
            raise BackupNotFoundError()
        path = self._resolve_within_backup_dir(record.path)
        if path is None or not path.exists():
            raise BackupNotFoundError()
        return record.file_name, path

    def _prune_expired(self, now: datetime) -> None:
        for record in self._registry.list_all():
            if record.expires_at <= now:
                self._discard(record)

    def _discard(self, record: BackupRecord) -> None:
        self._registry.discard(record.id)
        path = self._resolve_within_backup_dir(record.path)
        if path is not None:
            path.unlink(missing_ok=True)

    def _resolve_within_backup_dir(self, path: Path) -> Path | None:
        resolved_dir = self._settings.manual_backup_temp_dir.resolve()
        resolved_path = path.resolve()
        if resolved_path.parent != resolved_dir:
            return None
        return resolved_path


def cleanup_stale_manual_backups(settings: Settings) -> None:
    """Deletes leftover manual-backup files from a previous process.

    `BackupRegistry` is purely in-memory, so it is always empty right after
    a fresh start; any `*.db` file already sitting in this directory is
    necessarily orphaned from a run that never reached its 15-minute expiry
    (e.g. a crash), and is safe to delete unconditionally. Runs synchronously
    at startup alongside `ensure_runtime_directories`/`run_startup_migrations`
    (database.md §6: "在启动时清理残留").
    """
    directory = settings.manual_backup_temp_dir
    resolved_dir = directory.resolve()
    for path in directory.glob(_BACKUP_FILE_GLOB):
        resolved_path = path.resolve()
        if resolved_path.parent != resolved_dir:
            continue
        resolved_path.unlink(missing_ok=True)
