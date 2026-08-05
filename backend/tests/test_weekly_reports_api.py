from typing import Any, cast

from conftest import STAGE5_RUNTIME_HEADERS
from fastapi.testclient import TestClient

from app.core.config import Settings


def _create(client: TestClient, headers: dict[str, str], work_date: str) -> dict[str, Any]:
    response = client.post("/api/v1/daily-reports", headers=headers, json={"work_date": work_date})
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


def _default_content(report: dict[str, Any]) -> dict[str, object]:
    return {
        field["field_key"]: f"{field['label']}内容"
        for field in report["template_snapshot"]
        if field["enabled"] and field["required"]
    }


def _archive(client: TestClient, headers: dict[str, str], work_date: str) -> dict[str, Any]:
    report = _create(client, headers, work_date)
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
    archived = client.post(
        f"/api/v1/daily-reports/{report['id']}/archive",
        headers=headers,
        json={"version": submit.json()["data"]["version"]},
    )
    assert archived.status_code == 200, archived.text
    return cast(dict[str, Any], archived.json()["data"])


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
    assert create.status_code == 200, create.text
    login = client.post(
        "/api/v1/auth/login",
        headers=STAGE5_RUNTIME_HEADERS,
        json={"username": "alice", "password": "alice secure password"},
    )
    assert login.status_code == 200, login.text
    token = cast(str, login.json()["data"]["access_token"])
    return {**STAGE5_RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def test_availability_reports_per_day_status_archived_count_and_existing_report(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    _archive(client, headers, "2026-08-03")
    _create(client, headers, "2026-08-04")

    response = client.get(
        "/api/v1/weekly-reports/availability",
        headers=headers,
        params={"week_start": "2026-08-03"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["week_start"] == "2026-08-03"
    assert data["week_end"] == "2026-08-09"
    assert data["archived_count"] == 1
    assert data["non_archived_dates"] == ["2026-08-04"]
    assert data["existing_weekly_report_id"] is None
    statuses = {day["work_date"]: day["status"] for day in data["days"]}
    assert statuses["2026-08-03"] == "archived"
    assert statuses["2026-08-04"] == "draft"
    assert statuses["2026-08-05"] is None


def test_availability_rejects_a_non_monday_week_start(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    response = client.get(
        "/api/v1/weekly-reports/availability",
        headers=headers,
        params={"week_start": "2026-08-04"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_generate_creates_a_report_from_archived_days_only(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    archived = _archive(client, headers, "2026-08-03")
    _create(client, headers, "2026-08-04")

    response = client.post(
        "/api/v1/weekly-reports", headers=headers, json={"week_start": "2026-08-03"}
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["week_start"] == "2026-08-03"
    assert data["week_end"] == "2026-08-09"
    assert [day["work_date"] for day in data["content"]["days"]] == ["2026-08-03"]
    assert data["content"]["days"][0]["daily_report_id"] == archived["id"]
    assert data["content"] == data["generated_content"]


def test_generate_rejects_duplicate_week_with_existing_id(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    first = client.post(
        "/api/v1/weekly-reports", headers=headers, json={"week_start": "2026-08-03"}
    ).json()["data"]

    duplicate = client.post(
        "/api/v1/weekly-reports", headers=headers, json={"week_start": "2026-08-03"}
    )

    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "code": 40903,
        "msg": "该自然周周报已存在",
        "data": {"existing_weekly_report_id": first["id"]},
    }


def test_save_persists_free_text_and_rejects_stale_version(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    report = client.post(
        "/api/v1/weekly-reports", headers=headers, json={"week_start": "2026-08-03"}
    ).json()["data"]

    saved = client.put(
        f"/api/v1/weekly-reports/{report['id']}",
        headers=headers,
        json={
            "version": report["version"],
            "supplement": "补充说明",
            "next_week_plan": "下周计划",
            "risks": "风险项",
        },
    )
    assert saved.status_code == 200, saved.text
    saved_data = saved.json()["data"]
    assert saved_data["content"]["supplement"] == "补充说明"
    assert saved_data["version"] == report["version"] + 1

    stale = client.put(
        f"/api/v1/weekly-reports/{report['id']}",
        headers=headers,
        json={
            "version": report["version"],
            "supplement": "旧版本覆盖",
            "next_week_plan": "",
            "risks": "",
        },
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == 40904


def test_regenerate_requires_confirmation_and_then_overwrites(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context
    _archive(client, headers, "2026-08-03")
    report = client.post(
        "/api/v1/weekly-reports", headers=headers, json={"week_start": "2026-08-03"}
    ).json()["data"]
    edited = client.put(
        f"/api/v1/weekly-reports/{report['id']}",
        headers=headers,
        json={
            "version": report["version"],
            "supplement": "人工补充",
            "next_week_plan": "",
            "risks": "",
        },
    ).json()["data"]

    unconfirmed = client.post(
        f"/api/v1/weekly-reports/{report['id']}/regenerate",
        headers=headers,
        json={"version": edited["version"], "confirm_overwrite": False},
    )
    assert unconfirmed.status_code == 400
    assert unconfirmed.json()["code"] == 40001

    _archive(client, headers, "2026-08-05")
    regenerated = client.post(
        f"/api/v1/weekly-reports/{report['id']}/regenerate",
        headers=headers,
        json={"version": edited["version"], "confirm_overwrite": True},
    )
    assert regenerated.status_code == 200, regenerated.text
    regenerated_data = regenerated.json()["data"]
    assert regenerated_data["content"]["supplement"] == ""
    assert [day["work_date"] for day in regenerated_data["content"]["days"]] == [
        "2026-08-03",
        "2026-08-05",
    ]


def test_list_and_detail_are_owner_scoped(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    report = client.post(
        "/api/v1/weekly-reports", headers=admin_headers, json={"week_start": "2026-08-03"}
    ).json()["data"]
    alice_headers = _create_user_headers(client, admin_headers)

    alice_list = client.get("/api/v1/weekly-reports", headers=alice_headers)
    assert alice_list.status_code == 200
    assert alice_list.json()["data"]["items"] == []

    alice_detail = client.get(f"/api/v1/weekly-reports/{report['id']}", headers=alice_headers)
    assert alice_detail.status_code == 404
    assert alice_detail.json()["code"] == 40401

    admin_list = client.get("/api/v1/weekly-reports", headers=admin_headers)
    assert [item["id"] for item in admin_list.json()["data"]["items"]] == [report["id"]]


def test_weekly_routes_require_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.get(
        "/api/v1/weekly-reports/availability",
        headers={"X-Runtime-Secret": STAGE5_RUNTIME_HEADERS["X-Runtime-Secret"]},
        params={"week_start": "2026-08-03"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == 40102
