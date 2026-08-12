from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.schemas.template import TemplateFieldData

DailyStatus = Literal["draft", "submitted", "archived"]


class ProjectListEntry(BaseModel):
    """One row of a `PROJECT_LIST` field (`ai-docs/decisions.md` PROD-022,

    reshaped by PROD-028 and PROD-030). `project`/`content`
    (工作项目/工作步骤) are the only required fields. `category` defaults
    to `"重要"`; both completion dates default to `"当日"`, and
    `completion_notes` defaults to `"已完成"`. The remaining tracking
    fields default to `""`.
    """

    category: str = "重要"
    project: str
    content: str
    weight: str = ""
    planned_completion_date: str = "当日"
    actual_completion_date: str = "当日"
    owner: str = ""
    assistant: str = ""
    required_resources: str = ""
    completion_notes: str = "已完成"


type DailyFieldValue = str | int | float | list[str] | list[ProjectListEntry] | None
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
