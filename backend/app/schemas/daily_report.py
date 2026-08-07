from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

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
    client_request_id: str = Field(min_length=1, max_length=64)

    @field_validator("client_request_id")
    @classmethod
    def _strip_non_blank_client_request_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class DailySaveRequest(BaseModel):
    version: int = Field(ge=1)
    content: DailyInputContent


class DailyVersionRequest(BaseModel):
    version: int = Field(ge=1)


class DailyRevocationData(BaseModel):
    reason: str
    revoked_at: datetime
    actor_username: str

    @field_serializer("revoked_at")
    def _serialize_revoked_at(self, value: datetime) -> str:
        return _utc_iso(value) or ""


class DailyReportListItemData(BaseModel):
    id: str
    day_id: str
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
    day_id: str
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
    last_revocation: DailyRevocationData | None = None

    @field_serializer("submitted_at", "archived_at", "created_at", "updated_at")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return _utc_iso(value)


class DailyReportCreateData(DailyReportData):
    """`docs/方案设计.md` §6.2: creation replies must flag idempotent replays."""

    created: bool
