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


def _create_user_headers(
    client: TestClient, admin_headers: dict[str, str], username: str = "alice"
) -> dict[str, str]:
    create = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": "alice secure password",
            "display_name": "Alice",
            "role": "user",
        },
    )
    assert create.status_code == 200, create.text
    login = client.post(
        "/api/v1/auth/login",
        headers=STAGE5_RUNTIME_HEADERS,
        json={"username": username, "password": "alice secure password"},
    )
    assert login.status_code == 200, login.text
    token = cast(str, login.json()["data"]["access_token"])
    return {**STAGE5_RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def test_list_submitted_returns_metadata_without_content_or_template(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")
    submitted = _submit(client, alice_headers, report)

    response = client.get("/api/v1/admin/daily-reports/submitted", headers=admin_headers)

    assert response.status_code == 200, response.text
    items = response.json()["data"]["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == report["id"]
    assert item["owner_username"] == "alice"
    assert item["work_date"] == "2026-08-05"
    assert item["version"] == submitted["version"]
    assert "content" not in item
    assert "template_snapshot" not in item


def test_list_submitted_requires_admin_role(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)

    response = client.get("/api/v1/admin/daily-reports/submitted", headers=alice_headers)

    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_revoke_submission_returns_the_entry_to_draft_and_records_audit(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")
    submitted = _submit(client, alice_headers, report)

    revoke = client.post(
        f"/api/v1/admin/daily-reports/{report['id']}/revoke-submission",
        headers=admin_headers,
        json={"version": submitted["version"], "reason": "内容需要补充"},
    )
    assert revoke.status_code == 200, revoke.text

    owner_view = client.get(f"/api/v1/daily-reports/{report['id']}", headers=alice_headers)
    assert owner_view.status_code == 200
    detail = owner_view.json()["data"]
    assert detail["status"] == "draft"
    assert detail["submitted_at"] is None
    assert detail["content"] == submitted["content"]
    assert detail["last_revocation"]["reason"] == "内容需要补充"

    audit = client.get("/api/v1/admin/audit-events", headers=admin_headers)
    assert audit.status_code == 200, audit.text
    events = audit.json()["data"]["items"]
    assert len(events) == 1
    assert events[0]["action"] == "daily_submission_revoked"
    assert events[0]["target_id"] == report["id"]
    assert events[0]["target_owner_id"] is not None
    assert events[0]["reason"] == "内容需要补充"


def test_revoke_submission_requires_a_non_blank_reason(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")
    submitted = _submit(client, alice_headers, report)

    response = client.post(
        f"/api/v1/admin/daily-reports/{report['id']}/revoke-submission",
        headers=admin_headers,
        json={"version": submitted["version"], "reason": "   "},
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_revoke_submission_rejects_stale_version(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")
    submitted = _submit(client, alice_headers, report)

    response = client.post(
        f"/api/v1/admin/daily-reports/{report['id']}/revoke-submission",
        headers=admin_headers,
        json={"version": submitted["version"] + 1, "reason": "版本过期测试"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == 40904


def test_revoke_submission_requires_admin_role(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")
    submitted = _submit(client, alice_headers, report)

    response = client.post(
        f"/api/v1/admin/daily-reports/{report['id']}/revoke-submission",
        headers=alice_headers,
        json={"version": submitted["version"], "reason": "越权测试"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_revoke_submission_of_a_draft_is_rejected(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")

    response = client.post(
        f"/api/v1/admin/daily-reports/{report['id']}/revoke-submission",
        headers=admin_headers,
        json={"version": report["version"], "reason": "草稿不可撤销"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == 40401


def test_audit_events_can_be_filtered_by_action(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)
    report = _create(client, alice_headers, "2026-08-05")
    submitted = _submit(client, alice_headers, report)
    client.post(
        f"/api/v1/admin/daily-reports/{report['id']}/revoke-submission",
        headers=admin_headers,
        json={"version": submitted["version"], "reason": "过滤测试"},
    )

    matching = client.get(
        "/api/v1/admin/audit-events?action=daily_submission_revoked", headers=admin_headers
    )
    non_matching = client.get(
        "/api/v1/admin/audit-events?action=user_deleted", headers=admin_headers
    )

    assert len(matching.json()["data"]["items"]) == 1
    assert non_matching.json()["data"]["items"] == []


def test_audit_events_require_admin_role(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers)

    response = client.get("/api/v1/admin/audit-events", headers=alice_headers)

    assert response.status_code == 403
    assert response.json()["code"] == 40301
