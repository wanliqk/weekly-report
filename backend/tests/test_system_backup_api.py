from typing import cast

from conftest import STAGE5_RUNTIME_HEADERS
from fastapi.testclient import TestClient

from app.core.config import Settings


def _create_user_headers(
    client: TestClient, admin_headers: dict[str, str], *, username: str, role: str = "user"
) -> dict[str, str]:
    password = f"{username} secure password"
    create = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": password,
            "display_name": username.title(),
            "role": role,
        },
    )
    assert create.status_code == 200, create.text
    login = client.post(
        "/api/v1/auth/login",
        headers=STAGE5_RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    token = cast(str, login.json()["data"]["access_token"])
    return {**STAGE5_RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def test_admin_can_create_and_download_a_manual_backup(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, _settings = stage5_context

    created = client.post("/api/v1/system/backups", headers=headers)
    assert created.status_code == 200, created.text
    body = created.json()["data"]
    assert set(body.keys()) == {"id", "file_name", "expires_at"}
    assert body["file_name"].startswith("weekly-report-backup-")
    assert body["file_name"].endswith(".db")

    downloaded = client.get(f"/api/v1/system/backups/{body['id']}/file", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/vnd.sqlite3"
    assert body["file_name"] in downloaded.headers["content-disposition"]
    assert downloaded.content[:16] == b"SQLite format 3\x00"


def test_manual_backup_response_never_exposes_an_internal_path(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, headers, settings = stage5_context

    created = client.post("/api/v1/system/backups", headers=headers)
    assert created.status_code == 200, created.text
    payload_text = created.text
    assert str(settings.manual_backup_temp_dir) not in payload_text
    assert str(settings.data_dir) not in payload_text


def test_regular_user_cannot_create_or_download_manual_backups(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    alice_headers = _create_user_headers(client, admin_headers, username="alice")

    created_by_admin = client.post("/api/v1/system/backups", headers=admin_headers)
    assert created_by_admin.status_code == 200, created_by_admin.text
    backup_id = created_by_admin.json()["data"]["id"]

    create_attempt = client.post("/api/v1/system/backups", headers=alice_headers)
    download_attempt = client.get(f"/api/v1/system/backups/{backup_id}/file", headers=alice_headers)

    assert create_attempt.status_code == 403
    assert create_attempt.json()["code"] == 40301
    assert download_attempt.status_code == 403
    assert download_attempt.json()["code"] == 40301


def test_manual_backup_is_isolated_to_its_creating_admin(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, admin_headers, _settings = stage5_context
    second_admin_headers = _create_user_headers(client, admin_headers, username="bob", role="admin")

    created = client.post("/api/v1/system/backups", headers=admin_headers)
    backup_id = created.json()["data"]["id"]

    foreign_download = client.get(
        f"/api/v1/system/backups/{backup_id}/file", headers=second_admin_headers
    )

    assert foreign_download.status_code == 404
    assert foreign_download.json()["code"] == 40401


def test_manual_backup_routes_require_authentication(
    stage5_context: tuple[TestClient, dict[str, str], Settings],
) -> None:
    client, _headers, _settings = stage5_context
    response = client.post(
        "/api/v1/system/backups",
        headers={"X-Runtime-Secret": STAGE5_RUNTIME_HEADERS["X-Runtime-Secret"]},
    )
    assert response.status_code == 401
    assert response.json()["code"] == 40102
