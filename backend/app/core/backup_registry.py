"""In-process registry for manual full-database backup files.

`database.md` §6 is explicit that manual backups are a deliberate exception
to the rest of the app's persistence model: short-term download files are
never registered in a business table, they are mapped by a random in-process
ID, and they expire after 15 minutes with residual files cleaned up at
startup. A backup snapshot of the whole database has no business owner other
than "the admin who requested it a moment ago", so a plain in-memory
mapping — reset on every process restart, with
`services/backup.py::cleanup_stale_manual_backups` sweeping any leftover
files at startup — is the actual contract, not a shortcut around one.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class BackupRecord:
    id: str
    owner_id: str
    file_name: str
    path: Path
    created_at: datetime
    expires_at: datetime


class BackupRegistry:
    def __init__(self) -> None:
        self._records: dict[str, BackupRecord] = {}

    def add(self, record: BackupRecord) -> None:
        self._records[record.id] = record

    def get(self, backup_id: str) -> BackupRecord | None:
        return self._records.get(backup_id)

    def discard(self, backup_id: str) -> None:
        self._records.pop(backup_id, None)

    def list_all(self) -> list[BackupRecord]:
        return list(self._records.values())
