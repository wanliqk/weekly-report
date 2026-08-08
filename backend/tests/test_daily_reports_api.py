from typing import Any, cast

import pytest
from conftest import STAGE5_RUNTIME_HEADERS
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.ulid import generate_ulid


def _create(
    client: TestClient,
    headers: dict[str, str],
    work_date: str = "2026-08-05",
    client_request_id: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={
            "work_date": work_date,
            "client_request_id": client_request_id or generate_ulid(),
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _get(client: TestClient, headers: dict[str, str], report_id: str) -> dict[str, Any]:
    response = client.get(f"/api/v1/daily-reports/{report_id}", headers=headers)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _default_content(report: dict[str, Any]) -> dict[str, object]:
    return {
        field["field_key"]: f"{field['label']}内容"
        for field in report["template_snapshot"]
        if field["enabled"] and field["required"]
    }


def _save(
    client: TestClient,
    headers: dict[str, str],
    report: dict[str, Any],
    content: dict[str, object],
) -> dict[str, Any]:
    response = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": report["version"], "content": content},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _publish_project_list_field(
    client: TestClient, headers: dict[str, str], *, required: bool
) -> str:
    """Publishes an extra `PROJECT_LIST` field and returns its `field_key`."""
    current = client.get("/api/v1/report-templates/current", headers=headers)
    assert current.status_code == 200
    fields = cast(list[dict[str, Any]], current.json()["data"]["fields"])
    fields.append(
        {
            "label": "今日工作",
            "description": "",
            "field_type": "PROJECT_LIST",
            "required": required,
            "enabled": True,
            "sort_order": 100,
            "options": [],
        }
    )
    response = client.put(
        "/api/v1/report-templates/current", headers=headers, json={"fields": fields}
    )
    assert response.status_code == 200, response.text
    published_fields = cast(list[dict[str, Any]], response.json()["data"]["fields"])
    return cast(
        str,
        next(
            field["field_key"]
            for field in published_fields
            if field["field_type"] == "PROJECT_LIST"
        ),
    )


def _create_user_headers(client: TestClient, admin_headers: dict[str, str]) -> dict[str, str]:
    create = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "alice",
            "password": "alice secure password",
            "display_name": "Alice",
            "role": "user",
        },
    )
    assert create.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        headers=STAGE5_RUNTIME_HEADERS,
        json={"username": "alice", "password": "alice secure password"},
    )
    assert login.status_code == 200
    token = cast(str, login.json()["data"]["access_token"])
    return {**STAGE5_RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("work_date", ["2024-02-29", "2030-12-31", "2020-01-01"])
def test_create_supports_leap_future_and_historical_dates_and_allows_same_day_multiples(
    stage5_context: tuple[TestClient, dict[str, str], Settings], work_date: str
) -> None:
    client, headers, _settings = stage5_context
    created = _create(client, headers, work_date)

    second_entry = _create(client, headers, work_date)

    assert created["work_date"] == work_date
    assert created["status"] == "draft"
    assert created["created"] is True
    assert created["day_id"]
    assert second_entry["id"] != created["id"]
    assert second_entry["work_date"] == work_date
    assert second_entry["day_id"] == created["day_id"]


def test_create_replaying_the_same_client_request_id_is_idempotent(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    key = generate_ulid()

    first = _create(client, headers, "2026-08-05", key)
    second = _create(client, headers, "2026-08-05", key)

    assert first["id"] == second["id"]
    assert first["created"] is True
    assert second["created"] is False


def test_create_reusing_client_request_id_for_a_different_date_is_rejected(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    key = generate_ulid()
    _create(client, headers, "2026-08-05", key)

    conflict = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={"work_date": "2026-08-06", "client_request_id": key},
    )

    assert conflict.status_code == 409
    assert conflict.json()["code"] == 40908


def test_create_rejects_blank_client_request_id(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    response = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={"work_date": "2026-08-05", "client_request_id": "   "},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_save_list_filter_and_detail_restore_draft_content(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    older = _create(client, headers, "2026-08-04")
    newer = _create(client, headers, "2026-08-05")
    saved = _save(client, headers, newer, _default_content(newer))

    listing = client.get(
        "/api/v1/daily-reports?date_from=2026-08-05&date_to=2026-08-05&status=draft",
        headers=headers,
    )

    assert saved["version"] == 2
    assert _get(client, headers, newer["id"])["content"] == saved["content"]
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["data"]["items"]] == [newer["id"]]
    all_items = client.get("/api/v1/daily-reports", headers=headers).json()["data"]["items"]
    assert [item["id"] for item in all_items] == [newer["id"], older["id"]]


def test_invalid_date_range_is_rejected(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    response = client.get(
        "/api/v1/daily-reports?date_from=2026-08-06&date_to=2026-08-05",
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_draft_save_rejects_unknown_and_wrongly_typed_fields(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)
    field_key = report["template_snapshot"][0]["field_key"]

    for content in (
        {"01K000000000000000000000": "hidden"},
        {field_key: 42},
        {field_key: True},
        {field_key: {"nested": "value"}},
        {field_key: 10**1000},
    ):
        response = client.patch(
            f"/api/v1/daily-reports/{report['id']}",
            headers=headers,
            json={"version": 1, "content": content},
        )
        assert response.status_code == 422
        assert response.json()["code"] == 42201

    for non_finite in ("NaN", "Infinity"):
        response = client.patch(
            f"/api/v1/daily-reports/{report['id']}",
            headers={**headers, "Content-Type": "application/json"},
            content=(f'{{"version":1,"content":{{"{field_key}":{non_finite}}}}}'),
        )
        assert response.status_code == 422
        assert response.json()["code"] == 42201


def test_project_list_field_round_trips_valid_entries(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    """`ai-docs/decisions.md` PROD-022: saved/reloaded `PROJECT_LIST` values

    keep their `{project,content,status}` shape byte-for-byte.
    """
    client, headers, _settings = stage5_context
    field_key = _publish_project_list_field(client, headers, required=False)
    report = _create(client, headers)
    entries = [
        {"project": "个人日报系统", "content": "完成Excel导出功能", "status": "DONE"},
        {"project": "能源管理平台", "content": "设计设备接口", "status": "DOING"},
    ]

    saved = _save(client, headers, report, {field_key: entries})

    assert saved["content"][field_key] == entries
    assert _get(client, headers, report["id"])["content"][field_key] == entries


@pytest.mark.parametrize(
    "entries",
    [
        "not-a-list",
        [{"project": "", "content": "内容", "status": "DONE"}],
        [{"project": "项目", "content": "   ", "status": "DONE"}],
        [{"project": "项目", "content": "内容", "status": "UNKNOWN"}],
        [{"project": "项目", "content": "内容"}],
        [{"project": "项目", "content": "内容", "status": "DONE", "extra": "不该存在"}],
    ],
)
def test_project_list_field_rejects_malformed_entries(
    stage5_context: tuple[TestClient, dict[str, str], Settings], entries: object
) -> None:
    client, headers, _settings = stage5_context
    field_key = _publish_project_list_field(client, headers, required=False)
    report = _create(client, headers)

    response = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": report["version"], "content": {field_key: entries}},
    )

    assert response.status_code == 422
    assert response.json()["code"] == 42201


def test_project_list_required_field_blocks_submit_when_empty(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    field_key = _publish_project_list_field(client, headers, required=True)
    report = _create(client, headers)
    content = _default_content(report)
    content[field_key] = []
    saved = _save(client, headers, report, content)

    response = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": saved["version"]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == 42201


def test_project_list_field_submits_and_archives_with_multiple_entries(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    field_key = _publish_project_list_field(client, headers, required=True)
    report = _create(client, headers)
    content = _default_content(report)
    entries = [
        {"project": "个人日报系统", "content": "完成Excel导出功能", "status": "DONE"},
        {"project": "能源管理平台", "content": "设计设备接口", "status": "DOING"},
    ]
    content[field_key] = entries
    saved = _save(client, headers, report, content)

    submitted = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": saved["version"]},
    )
    assert submitted.status_code == 200, submitted.text

    archived = client.post(
        "/api/v1/daily-report-days/2026-08-05/archive",
        headers=headers,
        json={"confirm_archive": True},
    )
    assert archived.status_code == 200, archived.text
    snapshot_entries = archived.json()["data"]["archive_snapshot"]["entries"]
    assert snapshot_entries[0]["content"][field_key] == entries


def test_submit_validates_required_fields_and_preserves_draft_on_failure(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)

    response = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": report["version"]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == 42201
    assert len(response.json()["data"]["errors"]) == 2
    assert _get(client, headers, report["id"])["status"] == "draft"


def test_submit_does_not_auto_archive_and_leaves_the_day_open(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)
    report = _save(client, headers, report, _default_content(report))

    response = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": report["version"]},
    )
    submitted = response.json()["data"]

    assert submitted["status"] == "submitted"
    assert submitted["submitted_at"] is not None
    assert submitted["archived_at"] is None
    day = client.get("/api/v1/daily-report-days/2026-08-05", headers=headers).json()["data"]
    assert day["status"] == "open"
    assert day["can_archive"] is True


def test_removed_auto_archive_setting_returns_405(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    removed_setting = client.patch(
        "/api/v1/settings/me",
        headers=headers,
        json={"auto_archive_on_submit": True},
    )
    assert removed_setting.status_code == 405


def test_draft_can_be_deleted_and_then_no_longer_exists(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)

    deleted = client.request(
        "DELETE",
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": report["version"]},
    )
    assert deleted.status_code == 200

    missing = client.get(f"/api/v1/daily-reports/{report['id']}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == 40401


def test_submitted_entry_cannot_be_deleted(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)
    report = _save(client, headers, report, _default_content(report))
    submitted = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": report["version"]},
    ).json()["data"]

    response = client.request(
        "DELETE",
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": submitted["version"]},
    )
    assert response.status_code == 409
    assert response.json()["code"] == 40902


def test_stale_version_cannot_overwrite_newer_draft_content(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)
    first_content = _default_content(report)
    saved = _save(client, headers, report, first_content)

    conflict = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={
            "version": report["version"],
            "content": {next(iter(first_content)): "旧页面覆盖"},
        },
    )

    assert conflict.status_code == 409
    assert conflict.json()["code"] == 40904
    assert _get(client, headers, report["id"])["content"] == saved["content"]


def test_existing_daily_uses_its_snapshot_after_template_publish(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    first = _create(client, headers, "2026-08-04")
    current = client.get("/api/v1/report-templates/current", headers=headers).json()["data"]
    fields = current["fields"]
    fields[0]["label"] = "新版今日进展"
    published = client.put(
        "/api/v1/report-templates/current", headers=headers, json={"fields": fields}
    )
    assert published.status_code == 200
    second = _create(client, headers, "2026-08-05")

    assert _get(client, headers, first["id"])["template_snapshot"][0]["label"] == "今日工作内容"
    assert second["template_snapshot"][0]["label"] == "新版今日进展"


def test_daily_report_owner_isolation_returns_404(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    report = _create(client, admin_headers)
    alice_headers = _create_user_headers(client, admin_headers)

    response = client.get(f"/api/v1/daily-reports/{report['id']}", headers=alice_headers)
    assert response.status_code == 404
    assert response.json()["code"] == 40401


def test_daily_routes_require_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.get("/api/v1/daily-reports", headers={"X-Runtime-Secret": "r" * 32})
    assert response.status_code == 401
    assert response.json()["code"] == 40102
