import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import run_startup_migrations
from app.main import create_app

RUNTIME_SECRET = "r" * 32
JWT_SECRET = "j" * 64
RUNTIME_HEADERS = {"X-Runtime-Secret": RUNTIME_SECRET}
ADMIN_PASSWORD = "correct horse battery staple"
CHANGED_ADMIN_PASSWORD = "changed admin password"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    app_settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        runtime_secret=RUNTIME_SECRET,
    )
    ensure_runtime_directories(app_settings)
    run_startup_migrations(app_settings)
    return app_settings


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings, jwt_secret=JWT_SECRET)) as test_client:
        yield test_client


def _bootstrap(client: TestClient) -> None:
    response = client.post(
        "/api/v1/system/bootstrap",
        headers=RUNTIME_HEADERS,
        json={"username": "owner", "password": ADMIN_PASSWORD, "display_name": "Owner"},
    )
    assert response.status_code == 200


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(str, response.json()["data"]["access_token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def _admin_headers(client: TestClient) -> dict[str, str]:
    initial_headers = _auth_headers(_login(client, "admin", ADMIN_PASSWORD))
    changed = client.put(
        "/api/v1/auth/password",
        headers=initial_headers,
        json={
            "current_password": ADMIN_PASSWORD,
            "new_password": CHANGED_ADMIN_PASSWORD,
        },
    )
    assert changed.status_code == 200
    return _auth_headers(_login(client, "admin", CHANGED_ADMIN_PASSWORD))


def _create_user(
    client: TestClient,
    headers: dict[str, str],
    *,
    username: str = "alice",
    password: str = "alice secure password",
    role: str = "user",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": username,
            "password": password,
            "display_name": username.title(),
            "role": role,
        },
    )
    assert response.status_code == 200
    return cast(dict[str, object], response.json()["data"])


def test_admin_can_create_list_and_read_user_metadata_with_default_resources(
    client: TestClient, settings: Settings
) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)

    created = _create_user(client, headers)
    listed = client.get("/api/v1/users?page=1&page_size=1", headers=headers)
    detailed = client.get(f"/api/v1/users/{created['id']}", headers=headers)

    assert listed.status_code == 200
    list_data = listed.json()["data"]
    assert list_data["page"] == 1
    assert list_data["page_size"] == 1
    assert list_data["total"] == 3
    assert len(list_data["items"]) == 1
    assert detailed.status_code == 200
    assert detailed.json()["data"]["username"] == "alice"
    assert "password_hash" not in detailed.text

    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM user_settings WHERE user_id = ?", (created["id"],)
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM report_templates WHERE user_id = ?", (created["id"],)
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM template_versions WHERE created_by = ?",
            (created["id"],),
        ).fetchone() == (1,)


def test_duplicate_username_is_rejected_after_trim_and_casefold_without_partial_rows(
    client: TestClient, settings: Settings
) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    _create_user(client, headers, username="Alice")

    duplicate = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": " alice ",
            "password": "another secure password",
            "display_name": "Duplicate",
            "role": "user",
        },
    )

    assert duplicate.status_code == 400
    assert duplicate.json()["code"] == 40001
    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone() == (3,)
        assert connection.execute("SELECT COUNT(*) FROM user_settings").fetchone() == (3,)
        assert connection.execute("SELECT COUNT(*) FROM report_templates").fetchone() == (3,)


def test_user_creation_validates_username_length_after_trimming(client: TestClient) -> None:
    _bootstrap(client)

    response = client.post(
        "/api/v1/users",
        headers=_admin_headers(client),
        json={
            "username": "  ab  ",
            "password": "another secure password",
            "display_name": "Short",
            "role": "user",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_regular_user_cannot_call_admin_user_management(client: TestClient) -> None:
    _bootstrap(client)
    admin_headers = _admin_headers(client)
    _create_user(client, admin_headers)
    user_headers = _auth_headers(_login(client, "alice", "alice secure password"))

    response = client.get("/api/v1/users", headers=user_headers)

    assert response.status_code == 403
    assert response.json()["code"] == 40301


@pytest.mark.parametrize(
    "payload",
    [{"is_active": False}, {"role": "user"}],
)
def test_last_active_admin_cannot_be_disabled_or_demoted(
    client: TestClient, payload: dict[str, object]
) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    admin = client.get("/api/v1/auth/me", headers=headers).json()["data"]

    response = client.patch(f"/api/v1/users/{admin['id']}", headers=headers, json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == 40001
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_disabling_an_admin_with_another_active_admin_invalidates_the_old_token(
    client: TestClient,
) -> None:
    _bootstrap(client)
    first_admin_headers = _admin_headers(client)
    first_admin = client.get("/api/v1/auth/me", headers=first_admin_headers).json()["data"]
    second_admin = _create_user(
        client,
        first_admin_headers,
        username="admin-two",
        password="second admin password",
        role="admin",
    )

    response = client.patch(
        f"/api/v1/users/{first_admin['id']}",
        headers=first_admin_headers,
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=first_admin_headers).json()["code"] == 40102
    assert _login(client, str(second_admin["username"]), "second admin password")


def test_password_reset_invalidates_user_token_and_replaces_credentials(client: TestClient) -> None:
    _bootstrap(client)
    headers = _admin_headers(client)
    user = _create_user(client, headers)
    old_token = _login(client, "alice", "alice secure password")

    reset = client.put(
        f"/api/v1/users/{user['id']}/password",
        headers=headers,
        json={"new_password": "replacement password"},
    )

    assert reset.status_code == 200
    assert client.get("/api/v1/auth/me", headers=_auth_headers(old_token)).json()["code"] == 40102
    old_login = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": "alice", "password": "alice secure password"},
    )
    assert old_login.json()["code"] == 40101
    reset_token = _login(client, "alice", "replacement password")
    reset_headers = _auth_headers(reset_token)
    assert (
        client.get("/api/v1/auth/me", headers=reset_headers).json()["data"]["must_change_password"]
        is True
    )
    blocked = client.get("/api/v1/settings/me", headers=reset_headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == 40303

    changed = client.put(
        "/api/v1/auth/password",
        headers=reset_headers,
        json={
            "current_password": "replacement password",
            "new_password": "owner chosen password",
        },
    )
    assert changed.status_code == 200


def test_unknown_user_returns_404_without_account_details(client: TestClient) -> None:
    _bootstrap(client)

    response = client.get("/api/v1/users/01K000000000000000000000", headers=_admin_headers(client))

    assert response.status_code == 404
    assert response.json() == {"code": 40401, "msg": "用户不存在", "data": {}}


def test_user_list_flags_deletion_eligibility(client: TestClient) -> None:
    """`docs/方案设计.md` §7.3: the list must let the UI pre-disable delete."""
    _bootstrap(client)
    headers = _admin_headers(client)
    deletable = _create_user(client, headers, username="deletable")
    busy = _create_user(client, headers, username="busy")
    busy_headers = _auth_headers(_login(client, "busy", "alice secure password"))
    created_report = client.post(
        "/api/v1/daily-reports",
        headers=busy_headers,
        json={"work_date": "2026-08-05", "client_request_id": "user-list-eligibility-test"},
    )
    assert created_report.status_code == 200, created_report.text
    me = client.get("/api/v1/auth/me", headers=headers).json()["data"]

    listing = client.get("/api/v1/users", headers=headers)

    assert listing.status_code == 200, listing.text
    by_id = {item["id"]: item for item in listing.json()["data"]["items"]}
    assert by_id[me["id"]]["can_delete"] is False
    assert by_id[me["id"]]["cannot_delete_reason"] == "self"
    assert by_id[busy["id"]]["can_delete"] is False
    assert by_id[busy["id"]]["cannot_delete_reason"] == "has_business_records"
    assert by_id[deletable["id"]]["can_delete"] is True
    assert by_id[deletable["id"]]["cannot_delete_reason"] is None
