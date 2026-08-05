from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer

from app.schemas.template import TemplateFieldData

DailyStatus = Literal["draft", "submitted", "archived"]
type DailyFieldValue = str | int | float | list[str] | None
type DailyContent = dict[str, DailyFieldValue]
type DailyInputContent = dict[str, object]


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class DailyCreateRequest(BaseModel):
    work_date: date


class DailySaveRequest(BaseModel):
    version: int = Field(ge=1)
    content: DailyInputContent


class DailyVersionRequest(BaseModel):
    version: int = Field(ge=1)


class DailyReportListItemData(BaseModel):
    id: str
    work_date: date
    status: DailyStatus
    version: int
    updated_at: datetime
    submitted_at: datetime | None
    archived_at: datetime | None

    @field_serializer("updated_at", "submitted_at", "archived_at")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return _utc_iso(value)


class DailyReportListData(BaseModel):
    items: list[DailyReportListItemData]
    page: int
    page_size: int
    total: int


class DailyReportData(BaseModel):
    id: str
    work_date: date
    status: DailyStatus
    template_version_id: str
    template_snapshot: list[TemplateFieldData]
    content: DailyContent
    version: int
    submitted_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("submitted_at", "archived_at", "created_at", "updated_at")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return _utc_iso(value)
