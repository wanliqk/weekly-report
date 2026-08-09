"""Validation/serialization contracts for `wecom_sync_profiles`' three JSON columns.

`docs/方案设计.md` §6.3 requires each of `question_mapping_json`,
`recipient_config_json` and `field_mapping_json` to carry a `schema_version`
and be Pydantic-validated. `schema_version` is deliberately required (no
default) so a payload missing it fails validation instead of silently
defaulting to the current version.

These models are contracts only in this task (`WECOM-02`): nothing writes or
reads them through a Service yet. Future Service code is expected to call
`model_validate_json()` / `model_dump_json()` against `wecom_sync_profiles`
row values.
"""

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_serializer, model_validator

from app.integrations.wecom.schemas import WeComCookieIn

_FIELD_KEY_PATTERN = r"^[0-9A-HJKMNP-TV-Z]{26}$"

WeComReplyType = Literal["text", "date", "select"]
FieldMappingTarget = Literal["today_work", "tomorrow_plan", "ignore"]
UnmappedFieldPolicy = Literal["block", "ignore"]


class WeComQuestionSpec(BaseModel):
    """One target question (date/today/tomorrow) inside the remote form."""

    question_id: str = Field(min_length=1, max_length=64)
    reply_type: WeComReplyType
    sub_type: str | None = Field(default=None, max_length=64)
    submit_order: int = Field(ge=0, le=100)


class WeComQuestionMappingConfig(BaseModel):
    """`question_mapping_json`: which remote questions are date/today/tomorrow."""

    schema_version: Literal[1]
    date_question: WeComQuestionSpec
    today_question: WeComQuestionSpec
    tomorrow_question: WeComQuestionSpec

    @model_validator(mode="after")
    def _submit_orders_are_distinct(self) -> "WeComQuestionMappingConfig":
        orders = {
            self.date_question.submit_order,
            self.today_question.submit_order,
            self.tomorrow_question.submit_order,
        }
        if len(orders) != 3:
            raise ValueError("date/today/tomorrow questions must have distinct submit_order")
        return self


class WeComRecipientConfig(BaseModel):
    """`recipient_config_json`: `mngreporter`/`reporter` vid lists and their remote version."""

    schema_version: Literal[1]
    mngreporter_vids: list[str] = Field(default_factory=list)
    reporter_vids: list[str] = Field(default_factory=list)
    remote_version: int = Field(ge=0)

    @model_validator(mode="after")
    def _vids_are_non_blank(self) -> "WeComRecipientConfig":
        for vid in (*self.mngreporter_vids, *self.reporter_vids):
            if not vid.strip():
                raise ValueError("recipient vid must not be blank")
        return self


class WeComFieldMappingRule(BaseModel):
    """One stable local `field_key` routed to a target section (or ignored)."""

    field_key: str = Field(pattern=_FIELD_KEY_PATTERN)
    target: FieldMappingTarget


class WeComFieldMappingConfig(BaseModel):
    """`field_mapping_json`: `field_key -> today_work/tomorrow_plan/ignore` rules."""

    schema_version: Literal[1]
    rules: list[WeComFieldMappingRule] = Field(default_factory=list)
    unmapped_policy: UnmappedFieldPolicy = "block"

    @model_validator(mode="after")
    def _field_keys_are_unique(self) -> "WeComFieldMappingConfig":
        keys = [rule.field_key for rule in self.rules]
        if len(keys) != len(set(keys)):
            raise ValueError("field_key must appear at most once across rules")
        return self


# ---------------------------------------------------------------------------
# WECOM-06: public/Main-only REST request and response contracts
# (`docs/方案设计.md` §9.1/§9.2). The three config models above are the
# on-disk shape of `wecom_sync_profiles`' JSON columns; everything below is
# what actually crosses the wire.
# ---------------------------------------------------------------------------

WeComBindingStatus = Literal["connected", "expired", "disconnected"]
WeComSyncStatus = Literal[
    "pending",
    "syncing",
    "succeeded",
    "failed",
    "auth_required",
    "schema_changed",
    "duplicate_detected",
    "uncertain",
]


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


class WeComConnectionData(BaseModel):
    """`GET /api/v1/wecom/connection` response.

    `connected=False, status=None` means "no `wecom_user_bindings` row has
    ever existed for this user" — deliberately distinct from `status=
    "disconnected"` (a binding row exists, was connected before, and was
    explicitly disconnected). Neither case is an error; this endpoint always
    returns 200 (`docs/方案设计.md` §9.1: "本人连接状态和非敏感账号摘要").
    """

    connected: bool
    status: WeComBindingStatus | None
    wecom_vid: str | None
    display_name: str | None
    corp_id: str | None
    last_validated_at: datetime | None
    last_auth_error_at: datetime | None

    @field_serializer("last_validated_at", "last_auth_error_at")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return _utc_iso(value)


class WeComProfileData(BaseModel):
    """`GET /api/v1/wecom/profile` response — the three JSON columns
    deserialized into structured objects, never the raw JSON string."""

    form_id: str
    template_id: str
    destination_fingerprint: str
    schema_fingerprint: str
    question_mapping: WeComQuestionMappingConfig
    recipient_config: WeComRecipientConfig
    field_mapping: WeComFieldMappingConfig
    version: int
    is_active: bool


class WeComProfileUpdateRequest(BaseModel):
    """`PUT /api/v1/wecom/profile` request.

    `question_mapping` is deliberately not updatable here: it is discovered
    from the live remote template at connect time
    (`WeComConnectionService.validate_connection`), and §7.1 forbids
    resolving it from anything but that first-connect discovery ("标签匹配只
    用于首次配置时给出候选,不得把'名称包含计划'作为运行时规则"). `recipient_config`
    and `field_mapping` are the two things a user is actually meant to
    adjust after connecting.
    """

    expected_version: int = Field(ge=1)
    recipient_config: WeComRecipientConfig | None = None
    field_mapping: WeComFieldMappingConfig | None = None


class WeComPreviewRequest(BaseModel):
    daily_report_day_id: str = Field(min_length=1, max_length=64)


class WeComPreviewData(BaseModel):
    """`POST /api/v1/wecom/previews` response (`docs/方案设计.md` §5.2 step 3).

    Mirrors `WeComMappedPreview` (`app/services/wecom_mapper.py`) field for
    field — kept as a distinct schema rather than reusing that service-layer
    model directly, matching this codebase's existing convention of API
    response schemas living in `app/schemas/*.py` (see
    `app/services/daily_report_day.py`'s `DayDetail` dataclass -> the Router's
    own `DailyReportDayDetailData`). Never persisted, never logged.
    """

    date_answer: str
    today_work_answer: str
    tomorrow_plan_answer: str
    source_count: int
    today_work_char_count: int
    tomorrow_plan_char_count: int
    unmapped_field_keys: list[str]


class WeComSyncRecordData(BaseModel):
    """One `wecom_daily_sync_records` row. Never includes request/response
    bodies — the table itself doesn't store them (`docs/方案设计.md` §6.4)."""

    id: str
    daily_report_day_id: str
    work_date: date
    destination_fingerprint: str
    status: WeComSyncStatus
    attempt_count: int
    remote_answer_id: str | None
    remote_reply_id: str | None
    remote_journal_uuid: str | None
    last_error_kind: str | None
    last_error_message: str | None
    last_attempt_at: datetime | None
    succeeded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("last_attempt_at", "succeeded_at", "created_at", "updated_at")
    def _serialize_datetimes(self, value: datetime | None) -> str | None:
        return _utc_iso(value)


class WeComSyncRecordCreateData(WeComSyncRecordData):
    """`docs/方案设计.md` §10.1: creation is always idempotent, so the
    response must flag whether this call produced a brand-new `pending`
    record or returned an already-existing one (mirrors
    `DailyReportCreateData.created`)."""

    created: bool


class WeComSyncRecordListData(BaseModel):
    items: list[WeComSyncRecordData]
    page: int
    page_size: int
    total: int


# -- Main-only (`/api/v1/internal/wecom/**`) request/response contracts -----


class WeComConnectionValidateRequest(BaseModel):
    """Body of `POST /api/v1/internal/wecom/connections/validate`.

    `cookie_jar` reuses `WeComCookieIn` (`app/integrations/wecom/schemas.py`)
    rather than redefining an identical shape — its wire format already
    matches Electron's `serializeCookieJar()` exactly. `form_id` may
    legitimately be an empty string today: form discovery UI is `WECOM-07`
    scope, not this task's.
    """

    cookie_jar: list[WeComCookieIn]
    credential_slot: str = Field(min_length=1, max_length=64)
    form_id: str = Field(max_length=128)


class WeComSyncExecuteRequest(BaseModel):
    """Body of `POST /api/v1/internal/wecom/sync-records/{record_id}/execute`."""

    cookie_jar: list[WeComCookieIn]


class WeComInternalAckData(BaseModel):
    """Minimal Main-only response — `WeComBridgeClient` only cares whether
    the call was 2xx (`docs/方案设计.md` §5.1 step 6's "renderer 只收到非敏感账号...
    摘要" is served by the *public* `GET /wecom/connection` instead)."""

    status: str
