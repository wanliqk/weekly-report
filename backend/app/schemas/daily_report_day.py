from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, field_serializer

from app.schemas.daily_report import DailyContent, DailyReportListItemData
from app.schemas.template import TemplateFieldData

DailyReportDayStatus = Literal["open", "archived"]


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class DailyReportDayArchiveRequest(BaseModel):
    confirm_archive: bool


class DailyReportDayMonthItemData(BaseModel):
    """One row per date that already has a `daily_report_days` row.

    `docs/方案设计.md` §8.3: the month endpoint only returns dates with an
    existing record — a date absent from `items` has no record at all
    ("none"), which the caller derives itself rather than the server
    synthesizing an empty placeholder row for every calendar date.
    """

    work_date: date
    day_id: str
    status: DailyReportDayStatus
    draft_count: int
    submitted_count: int
    archived_count: int
    total_count: int
    can_create: bool
    can_archive: bool
    archive_disabled_reason: str | None


class DailyReportDayMonthData(BaseModel):
    month: str
    items: list[DailyReportDayMonthItemData]


class DayArchiveSnapshotEntryData(BaseModel):
    daily_report_id: str
    submitted_at: datetime
    template_version_id: str
    template_snapshot: list[TemplateFieldData]
    content: DailyContent

    @field_serializer("submitted_at")
    def _serialize_submitted_at(self, value: datetime) -> str:
        return _utc_iso(value) or ""


class DayArchiveSnapshotData(BaseModel):
    work_date: date
    entries: list[DayArchiveSnapshotEntryData]


class DailyReportDayDetailData(BaseModel):
    work_date: date
    status: DailyReportDayStatus
    draft_count: int
    submitted_count: int
    archived_count: int
    can_archive: bool
    archive_disabled_reason: str | None
    entries: list[DailyReportListItemData]
    archive_snapshot: DayArchiveSnapshotData | None
    archived_at: datetime | None

    @field_serializer("archived_at")
    def _serialize_archived_at(self, value: datetime | None) -> str | None:
        return _utc_iso(value)
