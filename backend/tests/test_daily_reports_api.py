from typing import Any, cast

import pytest
from conftest import STAGE5_RUNTIME_HEADERS
from fastapi.testclient import TestClient

from app.core.config import Settings


def _create(
    client: TestClient,
    headers: dict[str, str],
    work_date: str = "2026-08-05",
) -> dict[str, Any]:
    response = client.post("/api/v1/daily-reports", headers=headers, json={"work_date": work_date})
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
def test_create_supports_leap_future_and_historical_dates_and_rejects_duplicates(
    stage5_context: tuple[TestClient, dict[str, str], Settings], work_date: str
) -> None:
    client, headers, _settings = stage5_context
    created = _create(client, headers, work_date)

    duplicate = client.post("/api/v1/daily-reports", headers=headers, json={"work_date": work_date})

    assert created["work_date"] == work_date
    assert created["status"] == "draft"
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "code": 40901,
        "msg": "该工作日期已存在日报",
        "data": {"existing_report_id": created["id"]},
    }


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


def test_manual_submit_and_archive_follow_the_state_machine(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers)
    report = _save(client, headers, report, _default_content(report))

    submitted_response = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": report["version"]},
    )
    submitted = cast(dict[str, Any], submitted_response.json()["data"])
    archived_response = client.post(
        f"/api/v1/daily-reports/{report['id']}/archive",
        headers=headers,
        json={"version": submitted["version"]},
    )
    archived = cast(dict[str, Any], archived_response.json()["data"])

    assert submitted["status"] == "submitted"
    assert submitted["submitted_at"] is not None
    assert submitted["archived_at"] is None
    assert archived["status"] == "archived"
    assert archived["archived_at"] is not None
    invalid_save = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": archived["version"], "content": archived["content"]},
    )
    assert invalid_save.status_code == 409
    assert invalid_save.json()["code"] == 40902


def test_auto_archive_completes_submit_and_archive_in_one_transition(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    settings = client.patch(
        "/api/v1/settings/me",
        headers=headers,
        json={"auto_archive_on_submit": True},
    )
    assert settings.status_code == 200
    report = _create(client, headers)
    report = _save(client, headers, report, _default_content(report))

    response = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": report["version"]},
    )
    archived = response.json()["data"]

    assert archived["status"] == "archived"
    assert archived["submitted_at"] == archived["archived_at"]


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
