import json
from dataclasses import dataclass
from datetime import UTC, date, datetime

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.errors import AppError
from app.models import DailyReport, DailyReportDay
from app.repositories.daily_report import DailyReportRepository
from app.repositories.daily_report_day import DailyReportDayRepository
from app.schemas.daily_report_day import DailyReportDayStatus, DayArchiveSnapshotData

_SNAPSHOT_ADAPTER: TypeAdapter[DayArchiveSnapshotData] = TypeAdapter(DayArchiveSnapshotData)


class DailyReportDayNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40401, http_status=404, message="日期不存在")


class DailyReportDayArchiveNotConfirmedError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40001, http_status=400, message="日期级归档必须显式确认")


class DailyReportDayHasDraftsError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40906, http_status=409, message="当天仍有草稿 请先提交或删除")


class DailyReportDayNothingToArchiveError(AppError):
    def __init__(self) -> None:
        super().__init__(code=40907, http_status=409, message="当天没有可归档的条目")


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


@dataclass(frozen=True)
class DayMonthSummary:
    work_date: date
    status: DailyReportDayStatus | None
    draft_count: int
    submitted_count: int
    archived_count: int
    total_count: int
    can_create: bool
    can_archive: bool
    disabled_reason: str | None


@dataclass(frozen=True)
class DayDetail:
    work_date: date
    status: DailyReportDayStatus
    draft_count: int
    submitted_count: int
    archived_count: int
    can_archive: bool
    disabled_reason: str | None
    entries: list[DailyReport]
    archive_snapshot: DayArchiveSnapshotData | None
    archived_at: datetime | None


def build_day_archive_snapshot(work_date: date, entries: list[DailyReport]) -> str:
    """Pure function: folds a day's submitted entries into an immutable snapshot.

    Entries must already be sorted by `submitted_at ASC, id ASC` (the caller
    reads them via `DailyReportRepository.list_by_day`, which orders this
    way) so the snapshot's source order is stable and reproducible.
    """
    snapshot = {
        "schema_version": 2,
        "work_date": work_date.isoformat(),
        "entries": [
            {
                "daily_report_id": entry.id,
                "submitted_at": _utc_iso(entry.submitted_at)
                if entry.submitted_at is not None
                else None,
                "template_version_id": entry.template_version_id,
                "template_snapshot": json.loads(entry.template_snapshot_json),
                "content": json.loads(entry.content_json),
            }
            for entry in entries
        ],
    }
    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))


def parse_day_archive_snapshot(archive_snapshot_json: str) -> DayArchiveSnapshotData:
    try:
        return _SNAPSHOT_ADAPTER.validate_json(archive_snapshot_json)
    except ValidationError as error:
        raise RuntimeError("stored day archive snapshot is invalid") from error


def _open_day_summary(
    work_date: date, day: DailyReportDay | None, entries: list[DailyReport]
) -> DayMonthSummary:
    draft_count = sum(1 for entry in entries if entry.status == "draft")
    submitted_count = sum(1 for entry in entries if entry.status == "submitted")
    if draft_count > 0:
        can_archive = False
        disabled_reason: str | None = "存在草稿未提交"
    elif submitted_count == 0:
        can_archive = False
        disabled_reason = "尚无已提交条目"
    else:
        can_archive = True
        disabled_reason = None
    return DayMonthSummary(
        work_date=work_date,
        status="open" if day is not None else None,
        draft_count=draft_count,
        submitted_count=submitted_count,
        archived_count=0,
        total_count=len(entries),
        can_create=True,
        can_archive=can_archive,
        disabled_reason=disabled_reason,
    )


class DailyReportDayService:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._days = DailyReportDayRepository(session)
        self._reports = DailyReportRepository(session)

    async def get_for_owner(self, owner_id: str, work_date: date) -> DailyReportDay | None:
        return await self._days.get_for_owner_by_date(owner_id, work_date)

    async def month_summary(
        self, owner_id: str, *, month_start: date, month_end: date
    ) -> list[DayMonthSummary]:
        days = await self._days.list_month(owner_id, month_start=month_start, month_end=month_end)
        by_date = {day.work_date: day for day in days}
        items: list[DayMonthSummary] = []
        current = month_start
        while current <= month_end:
            day = by_date.get(current)
            if day is None:
                items.append(_open_day_summary(current, None, []))
            elif day.status == "archived":
                items.append(
                    DayMonthSummary(
                        work_date=current,
                        status="archived",
                        draft_count=0,
                        submitted_count=0,
                        archived_count=day.source_count,
                        total_count=day.source_count,
                        can_create=False,
                        can_archive=False,
                        disabled_reason="日期已归档",
                    )
                )
            else:
                entries = await self._reports.list_by_day(day.id)
                items.append(_open_day_summary(current, day, entries))
            current = date.fromordinal(current.toordinal() + 1)
        return items

    async def get_detail(self, owner_id: str, work_date: date) -> DayDetail:
        day = await self._days.get_for_owner_by_date(owner_id, work_date)
        entries = await self._reports.list_by_day(day.id) if day is not None else []
        if day is None:
            summary = _open_day_summary(work_date, None, entries)
            return DayDetail(
                work_date=work_date,
                status="open",
                draft_count=summary.draft_count,
                submitted_count=summary.submitted_count,
                archived_count=summary.archived_count,
                can_archive=summary.can_archive,
                disabled_reason=summary.disabled_reason,
                entries=entries,
                archive_snapshot=None,
                archived_at=None,
            )
        if day.status == "archived":
            snapshot = (
                parse_day_archive_snapshot(day.archive_snapshot_json)
                if day.archive_snapshot_json
                else None
            )
            return DayDetail(
                work_date=work_date,
                status="archived",
                draft_count=0,
                submitted_count=0,
                archived_count=day.source_count,
                can_archive=False,
                disabled_reason="日期已归档",
                entries=entries,
                archive_snapshot=snapshot,
                archived_at=day.archived_at,
            )
        summary = _open_day_summary(work_date, day, entries)
        return DayDetail(
            work_date=work_date,
            status="open",
            draft_count=summary.draft_count,
            submitted_count=summary.submitted_count,
            archived_count=0,
            can_archive=summary.can_archive,
            disabled_reason=summary.disabled_reason,
            entries=entries,
            archive_snapshot=None,
            archived_at=None,
        )

    async def archive(
        self, owner_id: str, work_date: date, *, confirm_archive: bool
    ) -> DailyReportDay:
        if not confirm_archive:
            raise DailyReportDayArchiveNotConfirmedError()
        day = await self._days.get_for_owner_by_date(owner_id, work_date)
        if day is None:
            raise DailyReportDayNotFoundError()
        if day.status == "archived":
            return day

        now = self._clock()
        reserved = await self._days.touch_open_for_write(day_id=day.id, owner_id=owner_id, now=now)
        if not reserved:
            await self._session.rollback()
            current = await self._days.get_for_owner_by_date(owner_id, work_date)
            if current is not None and current.status == "archived":
                return current
            raise DailyReportDayNotFoundError()

        entries = await self._reports.list_by_day(day.id)
        drafts = [entry for entry in entries if entry.status == "draft"]
        submitted = [entry for entry in entries if entry.status == "submitted"]
        if drafts:
            await self._session.rollback()
            raise DailyReportDayHasDraftsError()
        if not submitted:
            await self._session.rollback()
            raise DailyReportDayNothingToArchiveError()

        snapshot_json = build_day_archive_snapshot(work_date, submitted)
        await self._reports.archive_entries(day_id=day.id, archived_at=now)
        finalized = await self._days.finalize_archive(
            day_id=day.id,
            owner_id=owner_id,
            archive_snapshot_json=snapshot_json,
            source_count=len(submitted),
            archived_by=owner_id,
            archived_at=now,
        )
        if not finalized:
            await self._session.rollback()
            raise DailyReportDayNotFoundError()
        await self._session.commit()
        result = await self._days.get_for_owner_by_date(owner_id, work_date)
        assert result is not None
        return result
