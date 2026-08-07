from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, field_serializer

from app.schemas.daily_report import DailyFieldValue, DailyStatus


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class WeeklyDayField(BaseModel):
    field_key: str
    label: str
    value: DailyFieldValue


class WeeklyDayEntry(BaseModel):
    daily_report_id: str
    submitted_at: datetime | None
    fields: list[WeeklyDayField]

    @field_serializer("submitted_at")
    def _serialize_submitted_at(self, value: datetime | None) -> str | None:
        return _utc_iso(value)


class WeeklyDay(BaseModel):
    """One completed date's official result.

    `entries` may hold several source entries when the day was archived
    from multiple submitted entries (`docs/方案设计.md` §9.1); the day
    itself is still exactly one row here, matching the one-official-record-
    per-date rule.
    """

    work_date: date
    daily_report_day_id: str
    entries: list[WeeklyDayEntry]


class WeeklyContent(BaseModel):
    days: list[WeeklyDay]
    supplement: str = ""
    next_week_plan: str = ""
    risks: str = ""


class WeeklyGenerateRequest(BaseModel):
    week_start: date


class WeeklySaveRequest(BaseModel):
    version: int = Field(ge=1)
    supplement: str = Field(default="", max_length=10_000)
    next_week_plan: str = Field(default="", max_length=10_000)
    risks: str = Field(default="", max_length=10_000)


class WeeklyRegenerateRequest(BaseModel):
    version: int = Field(ge=1)
    confirm_overwrite: bool


class WeeklyAvailabilityDay(BaseModel):
    work_date: date
    status: DailyStatus | None


class WeeklyAvailabilityData(BaseModel):
    week_start: date
    week_end: date
    days: list[WeeklyAvailabilityDay]
    archived_count: int
    non_archived_dates: list[date]
    existing_weekly_report_id: str | None


class WeeklyReportListItemData(BaseModel):
    id: str
    week_start: date
    week_end: date
    version: int
    generated_at: datetime
    updated_at: datetime

    @field_serializer("generated_at", "updated_at")
    def _serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value) or ""


class WeeklyReportListData(BaseModel):
    items: list[WeeklyReportListItemData]
    page: int
    page_size: int
    total: int


class WeeklyReportData(BaseModel):
    id: str
    week_start: date
    week_end: date
    content: WeeklyContent
    generated_content: WeeklyContent
    version: int
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    @field_serializer("generated_at", "created_at", "updated_at")
    def _serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value) or ""
