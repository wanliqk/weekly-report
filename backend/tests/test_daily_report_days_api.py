from typing import Any, cast

from conftest import STAGE5_RUNTIME_HEADERS
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.ulid import generate_ulid


def _create(client: TestClient, headers: dict[str, str], work_date: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={"work_date": work_date, "client_request_id": generate_ulid()},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _default_content(report: dict[str, Any]) -> dict[str, object]:
    return {
        field["field_key"]: f"{field['label']}内容"
        for field in report["template_snapshot"]
        if field["enabled"] and field["required"]
    }


def _submit(client: TestClient, headers: dict[str, str], report: dict[str, Any]) -> dict[str, Any]:
    save = client.patch(
        f"/api/v1/daily-reports/{report['id']}",
        headers=headers,
        json={"version": report["version"], "content": _default_content(report)},
    )
    assert save.status_code == 200, save.text
    submit = client.post(
        f"/api/v1/daily-reports/{report['id']}/submit",
        headers=headers,
        json={"version": save.json()["data"]["version"]},
    )
    assert submit.status_code == 200, submit.text
    return cast(dict[str, Any], submit.json()["data"])


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


def test_month_summary_counts_by_status_across_the_whole_month(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    _create(client, headers, "2026-08-03")
    to_archive = _create(client, headers, "2026-08-05")
    _submit(client, headers, to_archive)
    archive = client.post(
        "/api/v1/daily-report-days/2026-08-05/archive",
        headers=headers,
        json={"confirm_archive": True},
    )
    assert archive.status_code == 200, archive.text

    response = client.get("/api/v1/daily-report-days?month=2026-08", headers=headers)
    assert response.status_code == 200, response.text
    items = {item["work_date"]: item for item in response.json()["data"]["items"]}

    assert len(items) == 31
    assert items["2026-08-01"]["status"] is None
    assert items["2026-08-01"]["can_create"] is True
    assert items["2026-08-03"]["status"] == "open"
    assert items["2026-08-03"]["draft_count"] == 1
    assert items["2026-08-03"]["can_archive"] is False
    assert items["2026-08-05"]["status"] == "archived"
    assert items["2026-08-05"]["archived_count"] == 1
    assert items["2026-08-05"]["can_create"] is False


def test_month_query_param_rejects_malformed_values(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    response = client.get("/api/v1/daily-report-days?month=2026-13", headers=headers)
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_day_detail_lists_open_entries_and_flags_archivability(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers, "2026-08-05")

    response = client.get("/api/v1/daily-report-days/2026-08-05", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "open"
    assert data["draft_count"] == 1
    assert data["can_archive"] is False
    assert data["disabled_reason"] == "存在草稿未提交"
    assert [item["id"] for item in data["entries"]] == [report["id"]]
    assert data["archive_snapshot"] is None


def test_day_archive_requires_no_drafts_and_at_least_one_submitted(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    with_draft_only = client.post(
        "/api/v1/daily-report-days/2026-08-06/archive",
        headers=headers,
        json={"confirm_archive": True},
    )
    assert with_draft_only.status_code == 404
    assert with_draft_only.json()["code"] == 40401

    report = _create(client, headers, "2026-08-05")
    _create(client, headers, "2026-08-05")
    _submit(client, headers, report)

    blocked = client.post(
        "/api/v1/daily-report-days/2026-08-05/archive",
        headers=headers,
        json={"confirm_archive": True},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == 40906


def test_day_archive_must_be_explicitly_confirmed(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = _create(client, headers, "2026-08-05")
    _submit(client, headers, report)

    unconfirmed = client.post(
        "/api/v1/daily-report-days/2026-08-05/archive",
        headers=headers,
        json={"confirm_archive": False},
    )
    assert unconfirmed.status_code == 400
    assert unconfirmed.json()["code"] == 40001

    missing_field = client.post(
        "/api/v1/daily-report-days/2026-08-05/archive", headers=headers, json={}
    )
    assert missing_field.status_code == 400


def test_day_archive_aggregates_multiple_submitted_entries_and_closes_the_day(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    first = _create(client, headers, "2026-08-05")
    second = _create(client, headers, "2026-08-05")
    _submit(client, headers, first)
    _submit(client, headers, second)

    response = client.post(
        "/api/v1/daily-report-days/2026-08-05/archive",
        headers=headers,
        json={"confirm_archive": True},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "archived"
    assert data["archived_count"] == 2
    assert data["archive_snapshot"] is not None
    assert {entry["daily_report_id"] for entry in data["archive_snapshot"]["entries"]} == {
        first["id"],
        second["id"],
    }
    assert {entry["status"] for entry in data["entries"]} == {"archived"}

    cannot_create = client.post(
        "/api/v1/daily-reports",
        headers=headers,
        json={"work_date": "2026-08-05", "client_request_id": generate_ulid()},
    )
    assert cannot_create.status_code == 409
    assert cannot_create.json()["code"] == 40905


def test_day_endpoints_isolate_owners(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    _create(client, admin_headers, "2026-08-05")
    alice_headers = _create_user_headers(client, admin_headers)

    detail = client.get("/api/v1/daily-report-days/2026-08-05", headers=alice_headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "open"
    assert detail.json()["data"]["entries"] == []

    month = client.get("/api/v1/daily-report-days?month=2026-08", headers=alice_headers)
    items = {item["work_date"]: item for item in month.json()["data"]["items"]}
    assert items["2026-08-05"]["status"] is None
