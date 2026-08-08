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

from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
