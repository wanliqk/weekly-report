from datetime import UTC, date, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, field_serializer, model_validator

ExportStatus = Literal["processing", "succeeded", "failed", "expired"]


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class ExportFilter(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    status: Literal["archived"] | None = None

    @model_validator(mode="after")
    def _validate_range(self) -> Self:
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("开始日期不能晚于结束日期")
        return self


class ExportCreateRequest(BaseModel):
    report_ids: list[str] | None = Field(default=None)
    filter: ExportFilter | None = None

    @model_validator(mode="after")
    def _validate_exclusive_selection(self) -> Self:
        if (self.report_ids is None) == (self.filter is None):
            raise ValueError("report_ids 与 filter 必须二选一")
        if self.report_ids is not None and len(self.report_ids) == 0:
            raise ValueError("report_ids 不能为空")
        return self


class ExportJobData(BaseModel):
    id: str
    status: ExportStatus
    record_count: int
    file_name: str | None
    created_at: datetime
    expires_at: datetime

    @field_serializer("created_at", "expires_at")
    def _serialize_datetimes(self, value: datetime) -> str:
        return _utc_iso(value)
