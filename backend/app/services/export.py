import asyncio
import json
import logging
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, as_naive_utc, utc_now
from app.core.config import Settings
from app.core.errors import AppError
from app.core.timezone import format_shanghai, to_shanghai
from app.core.ulid import generate_ulid
from app.models import DailyReportDay, ExportJob
from app.repositories.daily_report_day import DailyReportDayRepository
from app.repositories.export_job import ExportJobRepository
from app.repositories.user import UserRepository
from app.schemas.daily_report_day import DayArchiveSnapshotData
from app.schemas.export import ExportFilter
from app.schemas.template import TemplateFieldData
from app.services.daily_report_day import parse_day_archive_snapshot

logger = logging.getLogger(__name__)

EXPORT_EXPIRY = timedelta(hours=24)
EXPORT_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_SHEET_TITLE = "日报导出"
_MULTISELECT_SEPARATOR = "、"
_BASE_HEADERS = ["工作日期", "来源条目数", "提交时间", "归档时间"]


class ExportSelectionInvalidError(AppError):
    def __init__(self, invalid_daily_report_day_ids: list[str]) -> None:
        super().__init__(
            code=40001,
            http_status=400,
            message="所选日期中存在不属于本人或未归档的记录",
            data={"invalid_daily_report_day_ids": invalid_daily_report_day_ids},
        )


class ExportJobNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="导出任务不存在")


class ExportFileNotAvailableError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="导出文件不存在或已过期")


@dataclass(frozen=True)
class ExportColumn:
    field_key: str
    header: str


def plan_export_columns(snapshots: list[list[TemplateFieldData]]) -> list[ExportColumn]:
    """Merges every included entry's field snapshot into one ordered column list.

    `field_key` is immutable (database.md 3.4) so it is always the merge key;
    a field's *label* can change release to release, so the most recent
    snapshot that still carries the key wins for the displayed header
    (requirements.md 4.4.2: label changes must not affect merging). Column
    order follows first appearance across the chronologically ordered
    snapshots (day by day, entry by entry within a day), so fields still in
    use lead and fields only old entries used trail after them. Two distinct
    `field_key`s that happen to end up with the same header text get a short
    `field_key` suffix appended so the generated columns stay unambiguous.
    """
    order: dict[str, int] = {}
    label_by_key: dict[str, str] = {}
    next_index = 0
    for snapshot in snapshots:
        for field in sorted(snapshot, key=lambda item: item.sort_order):
            if field.field_key not in order:
                order[field.field_key] = next_index
                next_index += 1
            label_by_key[field.field_key] = field.label
    ordered_keys = sorted(order, key=lambda key: order[key])
    header_counts = Counter(label_by_key.values())
    columns: list[ExportColumn] = []
    for key in ordered_keys:
        label = label_by_key[key]
        if header_counts[label] > 1:
            label = f"{label}({key[-4:]})"
        columns.append(ExportColumn(field_key=key, header=label))
    return columns


def _defuse_formula(text: str) -> str:
    """Neutralizes a cell that would otherwise be a live Excel formula.

    openpyxl auto-promotes any string starting with `=` to a formula cell
    (CWE-1236 "Excel formula injection"); report text is free-form user
    input, so a value like `=HYPERLINK(...)` would execute when the
    exported file is later opened by someone else. A leading apostrophe is
    the standard "force text" escape Excel itself uses for this. `+`/`-`/
    `@` prefixes are deliberately left alone: unlike CSV, openpyxl does not
    promote them to formulas, and `-`/`+` are extremely common as bullet or
    list markers in Chinese report text — defusing them would corrupt
    ordinary content for no safety benefit.
    """
    return f"'{text}" if text.startswith("=") else text


def _single_source_cell(value: object) -> str | int | float | None:
    if value is None:
        return None
    if isinstance(value, list):
        return _defuse_formula(_MULTISELECT_SEPARATOR.join(str(item) for item in value))
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int | float):
        return value
    return _defuse_formula(str(value))


def _multi_source_cell(
    values_by_position: Sequence[tuple[int, object]],
) -> str | int | float | None:
    """Renders a field/column that may carry values from several of a day's

    source entries. `docs/方案设计.md` §9.2: a single value keeps its native
    type (so numeric columns stay numeric); two or more values are written
    as one text cell, one `[N] value` line per source, preserving which
    numbered source (1-based, by submission order) each value came from.
    """
    present = [
        (position, cell)
        for position, raw in values_by_position
        if (cell := _single_source_cell(raw)) is not None
    ]
    if not present:
        return None
    if len(present) == 1:
        return present[0][1]
    return "\n".join(f"[{position}] {value}" for position, value in present)


def build_export_workbook(days: list[DailyReportDay], columns: list[ExportColumn]) -> bytes:
    """Pure, blocking xlsx builder — callers must run it off the event loop."""
    workbook = Workbook()
    sheet = workbook.active
    if sheet is None:  # pragma: no cover - a fresh Workbook() always has an active sheet
        raise RuntimeError("workbook has no active worksheet")
    sheet.title = _SHEET_TITLE
    sheet.append([*_BASE_HEADERS, *(column.header for column in columns)])
    for day in days:
        snapshot: DayArchiveSnapshotData = parse_day_archive_snapshot(
            day.archive_snapshot_json or ""
        )
        entries = snapshot.entries
        submitted_times = _multi_source_cell(
            [
                (index + 1, format_shanghai(entry.submitted_at))
                for index, entry in enumerate(entries)
            ]
        )
        row: list[str | int | float | None] = [
            day.work_date.isoformat(),
            len(entries),
            submitted_times,
            format_shanghai(day.archived_at) if day.archived_at else "",
        ]
        for column in columns:
            values_by_position = [
                (index + 1, entry.content.get(column.field_key))
                for index, entry in enumerate(entries)
            ]
            row.append(_multi_source_cell(values_by_position))
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9一-鿿]+")


def _safe_filename_component(username: str) -> str:
    """Keeps the export file name inside the Electron save-dialog whitelist

    (`electron/src/main/export/file-saver.ts`'s `SAFE_FILE_NAME_PATTERN`)
    regardless of what characters the username itself contains — usernames
    have no character restriction beyond length (`app/schemas/user.py`).
    """
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", username).strip("_")
    return cleaned or "user"


def _export_file_name(username: str, target_date: date) -> str:
    safe_username = _safe_filename_component(username)
    return f"日报-{safe_username}_{target_date.year}年{target_date.month}月{target_date.day}日.xlsx"


class ExportService:
    def __init__(
        self, session: AsyncSession, settings: Settings, *, clock: Clock = utc_now
    ) -> None:
        self._session = session
        self._settings = settings
        self._clock = clock
        self._days = DailyReportDayRepository(session)
        self._jobs = ExportJobRepository(session)
        self._users = UserRepository(session)

    async def create(
        self,
        owner_id: str,
        *,
        daily_report_day_ids: list[str] | None,
        filter_: ExportFilter | None,
    ) -> ExportJob:
        days = await self._resolve_days(
            owner_id, daily_report_day_ids=daily_report_day_ids, filter_=filter_
        )
        snapshots = [
            entry.template_snapshot
            for day in days
            for entry in parse_day_archive_snapshot(day.archive_snapshot_json or "").entries
        ]
        columns = plan_export_columns(snapshots)

        now = self._clock()
        job = ExportJob(
            id=generate_ulid(),
            user_id=owner_id,
            status="processing",
            request_json=json.dumps(
                {"daily_report_day_ids": daily_report_day_ids}
                if daily_report_day_ids is not None
                else {"filter": (filter_ or ExportFilter()).model_dump(mode="json")},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            record_count=0,
            created_at=now,
            expires_at=now + EXPORT_EXPIRY,
        )

        file_path = self._settings.export_temp_dir / f"{job.id}.xlsx"
        try:
            file_bytes = await asyncio.to_thread(build_export_workbook, days, columns)
            await asyncio.to_thread(file_path.write_bytes, file_bytes)
        except Exception:
            logger.exception("export file generation failed")
            job.status = "failed"
            job.error_message = "导出文件生成失败"
        else:
            user = await self._users.get_by_id(owner_id)
            assert user is not None
            target_date = max((day.work_date for day in days), default=to_shanghai(now).date())
            job.status = "succeeded"
            job.file_name = _export_file_name(user.username, target_date)
            job.file_path = str(file_path)
            job.record_count = len(days)

        await self._jobs.add(job)
        await self._session.commit()
        return job

    async def get(self, owner_id: str, job_id: str) -> ExportJob:
        job = await self._jobs.get_for_owner(job_id, owner_id)
        if job is None:
            raise ExportJobNotFoundError()
        await self._expire_if_needed(job)
        return job

    async def get_download(self, owner_id: str, job_id: str) -> tuple[str, Path]:
        job = await self.get(owner_id, job_id)
        if job.status != "succeeded" or job.file_path is None or job.file_name is None:
            raise ExportFileNotAvailableError()
        path = self._resolve_within_export_dir(Path(job.file_path))
        if path is None or not path.exists():
            raise ExportFileNotAvailableError()
        return job.file_name, path

    async def cleanup_expired(self) -> None:
        now = as_naive_utc(self._clock())
        jobs = await self._jobs.list_expired_with_files(now=now)
        for job in jobs:
            self._delete_export_file(job)
            job.status = "expired"
            job.file_path = None
        if jobs:
            await self._session.commit()

    async def _resolve_days(
        self,
        owner_id: str,
        *,
        daily_report_day_ids: list[str] | None,
        filter_: ExportFilter | None,
    ) -> list[DailyReportDay]:
        if daily_report_day_ids is not None:
            unique_ids = list(dict.fromkeys(daily_report_day_ids))
            days = await self._days.get_by_ids_for_owner_archived(owner_id, unique_ids)
            found_ids = {day.id for day in days}
            missing = [day_id for day_id in unique_ids if day_id not in found_ids]
            if missing:
                raise ExportSelectionInvalidError(missing)
            return days
        resolved_filter = filter_ or ExportFilter()
        return await self._days.list_archived_in_range(
            owner_id, date_from=resolved_filter.date_from, date_to=resolved_filter.date_to
        )

    async def _expire_if_needed(self, job: ExportJob) -> None:
        if job.status != "succeeded" or job.expires_at > as_naive_utc(self._clock()):
            return
        self._delete_export_file(job)
        job.status = "expired"
        job.file_path = None
        await self._session.commit()

    def _delete_export_file(self, job: ExportJob) -> None:
        if job.file_path is None:
            return
        path = self._resolve_within_export_dir(Path(job.file_path))
        if path is not None:
            path.unlink(missing_ok=True)

    def _resolve_within_export_dir(self, path: Path) -> Path | None:
        resolved_dir = self._settings.export_temp_dir.resolve()
        resolved_path = path.resolve()
        if resolved_path.parent != resolved_dir:
            return None
        return resolved_path
