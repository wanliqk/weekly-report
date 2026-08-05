import json
import sqlite3
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings


def _current(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.get("/api/v1/report-templates/current", headers=headers)
    assert response.status_code == 200
    return cast(dict[str, object], response.json()["data"])


def _publish(
    client: TestClient, headers: dict[str, str], fields: list[dict[str, object]]
) -> dict[str, object]:
    response = client.put(
        "/api/v1/report-templates/current", headers=headers, json={"fields": fields}
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, object], response.json()["data"])


def test_default_template_and_new_version_keep_stable_keys(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, settings = stage5_context
    current = _current(client, headers)
    fields = cast(list[dict[str, Any]], current["fields"])
    assert [field["core_type"] for field in fields] == ["today_work", "tomorrow_plan"]
    original_keys = [field["field_key"] for field in fields]

    publish_fields = [
        {
            **field,
            "label": "今日进展" if field["core_type"] == "today_work" else field["label"],
        }
        for field in fields
    ]
    publish_fields.append(
        {
            "label": "投入小时",
            "description": "",
            "field_type": "number",
            "required": False,
            "enabled": True,
            "sort_order": 30,
            "options": [],
        }
    )
    published = _publish(client, headers, publish_fields)

    assert published["version_no"] == 2
    published_fields = cast(list[dict[str, Any]], published["fields"])
    assert [field["field_key"] for field in published_fields[:2]] == original_keys
    assert len(str(published_fields[2]["field_key"])) == 26
    versions = client.get("/api/v1/report-templates/versions", headers=headers).json()["data"]
    assert [item["version_no"] for item in versions["items"]] == [2, 1]

    with sqlite3.connect(settings.database_path) as connection:
        version_one = connection.execute(
            "SELECT fields_json FROM template_versions WHERE version_no = 1"
        ).fetchone()
        assert version_one is not None
        assert json.loads(version_one[0])[0]["label"] == "今日工作内容"


@pytest.mark.parametrize("mutation", ["remove_core", "disable_cores"])
def test_core_fields_cannot_be_removed_or_all_disabled(
    stage5_context: tuple[TestClient, dict[str, str], Settings], mutation: str
) -> None:
    client, headers, _settings = stage5_context
    fields = cast(list[dict[str, Any]], _current(client, headers)["fields"])
    payload = (
        fields[1:]
        if mutation == "remove_core"
        else [{**field, "enabled": False} for field in fields]
    )

    response = client.put(
        "/api/v1/report-templates/current", headers=headers, json={"fields": payload}
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001
    assert _current(client, headers)["version_no"] == 1


@pytest.mark.parametrize(
    "field",
    [
        {
            "label": "类型错误",
            "field_type": "text",
            "sort_order": 30,
            "options": ["不该存在"],
        },
        {
            "label": "无选项",
            "field_type": "select",
            "sort_order": 30,
            "options": [],
        },
        {
            "label": "重复选项",
            "field_type": "multiselect",
            "sort_order": 30,
            "options": ["开发", " 开发 "],
        },
    ],
)
def test_template_field_options_are_validated(
    stage5_context: tuple[TestClient, dict[str, str], Settings], field: dict[str, object]
) -> None:
    client, headers, _settings = stage5_context
    current_fields = cast(list[dict[str, Any]], _current(client, headers)["fields"])
    response = client.put(
        "/api/v1/report-templates/current",
        headers=headers,
        json={
            "fields": [
                *current_fields,
                {
                    "description": "",
                    "required": False,
                    "enabled": True,
                    **field,
                },
            ]
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_template_requires_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.get(
        "/api/v1/report-templates/current", headers={"X-Runtime-Secret": "r" * 32}
    )
    assert response.status_code == 401
    assert response.json()["code"] == 40102
