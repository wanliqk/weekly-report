from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, field_validator

FieldType = Literal["text", "textarea", "number", "date", "select", "multiselect", "PROJECT_LIST"]
CoreType = Literal["today_work", "tomorrow_plan"]


class TemplateFieldInput(BaseModel):
    field_key: str | None = Field(
        default=None,
        pattern=r"^[0-9A-HJKMNP-TV-Z]{26}$",
        description="Existing stable key; omit for a new field.",
    )
    label: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    field_type: FieldType
    required: bool = False
    enabled: bool = True
    show_in_export: bool = True
    sort_order: int = Field(ge=0, le=10_000)
    options: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("label")
    @classmethod
    def _strip_non_blank_label(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("description")
    @classmethod
    def _strip_description(cls, value: str) -> str:
        return value.strip()


class TemplateFieldData(BaseModel):
    field_key: str
    label: str
    description: str
    field_type: FieldType
    required: bool
    enabled: bool
    show_in_export: bool = True
    sort_order: int
    options: list[str]
    core_type: CoreType | None = None


class TemplatePublishRequest(BaseModel):
    fields: list[TemplateFieldInput] = Field(min_length=1, max_length=100)


class TemplateCurrentData(BaseModel):
    id: str
    name: str
    version_no: int
    fields: list[TemplateFieldData]


class TemplateVersionSummaryData(BaseModel):
    id: str
    version_no: int
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()


class TemplateVersionsData(BaseModel):
    items: list[TemplateVersionSummaryData]
