from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.wecom import (
    WeComFieldMappingConfig,
    WeComQuestionMappingConfig,
    WeComRecipientConfig,
)

_VALID_FIELD_KEY = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _question_mapping_payload(**overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "date_question": {"question_id": "q1", "reply_type": "date", "submit_order": 0},
        "today_question": {"question_id": "q2", "reply_type": "text", "submit_order": 1},
        "tomorrow_question": {"question_id": "q3", "reply_type": "text", "submit_order": 2},
    }
    payload.update(overrides)
    return payload


def _recipient_config_payload(**overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "mngreporter_vids": ["1000001"],
        "reporter_vids": ["1000002", "1000003"],
        "remote_version": 1,
    }
    payload.update(overrides)
    return payload


def _field_mapping_payload(**overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "rules": [{"field_key": _VALID_FIELD_KEY, "target": "today_work"}],
        "unmapped_policy": "block",
    }
    payload.update(overrides)
    return payload


def test_question_mapping_config_accepts_a_valid_payload() -> None:
    config = WeComQuestionMappingConfig.model_validate(_question_mapping_payload())

    assert config.schema_version == 1
    assert config.date_question.reply_type == "date"
    assert config.today_question.submit_order == 1


def test_question_mapping_config_round_trips_through_json() -> None:
    config = WeComQuestionMappingConfig.model_validate(_question_mapping_payload())

    restored = WeComQuestionMappingConfig.model_validate_json(config.model_dump_json())

    assert restored == config


def test_question_mapping_config_rejects_a_missing_schema_version() -> None:
    payload = _question_mapping_payload()
    del payload["schema_version"]

    with pytest.raises(ValidationError):
        WeComQuestionMappingConfig.model_validate(payload)


def test_question_mapping_config_rejects_an_unsupported_schema_version() -> None:
    with pytest.raises(ValidationError):
        WeComQuestionMappingConfig.model_validate(_question_mapping_payload(schema_version=2))


def test_question_mapping_config_rejects_a_non_integer_submit_order() -> None:
    payload = _question_mapping_payload()
    payload["today_question"]["submit_order"] = "first"

    with pytest.raises(ValidationError):
        WeComQuestionMappingConfig.model_validate(payload)


def test_question_mapping_config_rejects_duplicate_submit_orders() -> None:
    payload = _question_mapping_payload()
    payload["tomorrow_question"]["submit_order"] = payload["today_question"]["submit_order"]

    with pytest.raises(ValidationError, match="distinct submit_order"):
        WeComQuestionMappingConfig.model_validate(payload)


def test_question_mapping_config_rejects_an_unknown_reply_type() -> None:
    payload = _question_mapping_payload()
    payload["date_question"]["reply_type"] = "voice"

    with pytest.raises(ValidationError):
        WeComQuestionMappingConfig.model_validate(payload)


def test_recipient_config_accepts_a_valid_payload() -> None:
    config = WeComRecipientConfig.model_validate(_recipient_config_payload())

    assert config.mngreporter_vids == ["1000001"]
    assert config.reporter_vids == ["1000002", "1000003"]


def test_recipient_config_rejects_a_missing_schema_version() -> None:
    payload = _recipient_config_payload()
    del payload["schema_version"]

    with pytest.raises(ValidationError):
        WeComRecipientConfig.model_validate(payload)


def test_recipient_config_rejects_a_blank_vid() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        WeComRecipientConfig.model_validate(_recipient_config_payload(reporter_vids=["   "]))


def test_recipient_config_rejects_a_non_list_vid_field() -> None:
    with pytest.raises(ValidationError):
        WeComRecipientConfig.model_validate(_recipient_config_payload(reporter_vids="1000002"))


def test_field_mapping_config_accepts_a_valid_payload() -> None:
    config = WeComFieldMappingConfig.model_validate(_field_mapping_payload())

    assert config.rules[0].field_key == _VALID_FIELD_KEY
    assert config.rules[0].target == "today_work"
    assert config.unmapped_policy == "block"


def test_field_mapping_config_defaults_unmapped_policy_to_block() -> None:
    payload = _field_mapping_payload()
    del payload["unmapped_policy"]

    config = WeComFieldMappingConfig.model_validate(payload)

    assert config.unmapped_policy == "block"


def test_field_mapping_config_rejects_a_missing_schema_version() -> None:
    payload = _field_mapping_payload()
    del payload["schema_version"]

    with pytest.raises(ValidationError):
        WeComFieldMappingConfig.model_validate(payload)


def test_field_mapping_config_rejects_a_malformed_field_key() -> None:
    payload = _field_mapping_payload()
    payload["rules"][0]["field_key"] = "not-a-ulid"

    with pytest.raises(ValidationError):
        WeComFieldMappingConfig.model_validate(payload)


def test_field_mapping_config_rejects_an_unknown_target() -> None:
    payload = _field_mapping_payload()
    payload["rules"][0]["target"] = "delete"

    with pytest.raises(ValidationError):
        WeComFieldMappingConfig.model_validate(payload)


def test_field_mapping_config_rejects_duplicate_field_keys() -> None:
    payload = _field_mapping_payload(
        rules=[
            {"field_key": _VALID_FIELD_KEY, "target": "today_work"},
            {"field_key": _VALID_FIELD_KEY, "target": "tomorrow_plan"},
        ]
    )

    with pytest.raises(ValidationError, match="at most once"):
        WeComFieldMappingConfig.model_validate(payload)
