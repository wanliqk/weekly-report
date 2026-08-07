from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, field_serializer, field_validator


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class AdminDailyReportSubmittedItemData(BaseModel):
    id: str
    owner_id: str
    owner_username: str
    owner_display_name: str
    work_date: date
    submitted_at: datetime | None
    version: int

    @field_serializer("submitted_at")
    def _serialize_submitted_at(self, value: datetime | None) -> str | None:
        return _utc_iso(value)


class AdminDailyReportSubmittedListData(BaseModel):
    items: list[AdminDailyReportSubmittedItemData]
    page: int
    page_size: int
    total: int


class AdminDailyReportRevokeRequest(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip_non_blank_reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class AdminAuditEventData(BaseModel):
    id: str
    action: str
    actor_username_snapshot: str
    target_type: str
    target_id: str
    target_owner_id: str | None
    reason: str
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return _utc_iso(value) or ""


class AdminAuditEventListData(BaseModel):
    items: list[AdminAuditEventData]
    page: int
    page_size: int
    total: int
