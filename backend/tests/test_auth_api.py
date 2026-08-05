from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from app.core.access_token import encode_access_token
from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import run_startup_migrations
from app.main import create_app

RUNTIME_SECRET = "r" * 32
JWT_SECRET = "j" * 64
RUNTIME_HEADERS = {"X-Runtime-Secret": RUNTIME_SECRET}


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        runtime_secret=RUNTIME_SECRET,
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    with TestClient(create_app(settings, jwt_secret=JWT_SECRET)) as test_client:
        yield test_client


def _bootstrap(client: TestClient) -> None:
    response = client.post(
        "/api/v1/system/bootstrap-admin",
        headers=RUNTIME_HEADERS,
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Admin",
        },
    )
    assert response.status_code == 200


def _login(
    client: TestClient,
    *,
    username: str = "admin",
    password: str = "correct horse battery staple",
) -> str:
    response = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return cast(str, response.json()["data"]["access_token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {**RUNTIME_HEADERS, "Authorization": f"Bearer {token}"}


def test_login_and_me_return_only_safe_account_metadata(client: TestClient) -> None:
    _bootstrap(client)

    token = _login(client, username=" ADMIN ")
    response = client.get("/api/v1/auth/me", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    data = response.json()["data"]
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["created_at"].endswith("+00:00")
    assert "password" not in data
    assert "password_hash" not in data
    assert "token_version" not in data


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("missing", "correct horse battery staple"),
        ("admin", "wrong password"),
    ],
)
def test_login_uses_the_same_public_error_for_unknown_user_and_wrong_password(
    client: TestClient, username: str, password: str
) -> None:
    _bootstrap(client)

    response = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": username, "password": password},
    )

    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_business_requests_require_both_runtime_secret_and_bearer_token(
    client: TestClient,
) -> None:
    _bootstrap(client)
    token = _login(client)

    assert client.get("/api/v1/auth/me", headers=RUNTIME_HEADERS).json()["code"] == 40102
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == 40103


def test_expired_and_tampered_tokens_map_to_40102(client: TestClient) -> None:
    _bootstrap(client)
    valid_token = _login(client)
    replacement = "a" if valid_token[-1] != "a" else "b"
    expired_token = encode_access_token(
        user_id="01K000000000000000000000",
        role="admin",
        token_version=1,
        secret=JWT_SECRET,
        clock=lambda: datetime.now(UTC) - timedelta(days=2),
    ).token

    for token in (valid_token[:-1] + replacement, expired_token):
        response = client.get("/api/v1/auth/me", headers=_auth_headers(token))
        assert response.status_code == 401
        assert response.json()["code"] == 40102


def test_change_password_invalidates_the_current_token_and_old_password(
    client: TestClient,
) -> None:
    _bootstrap(client)
    token = _login(client)

    wrong_current = client.put(
        "/api/v1/auth/password",
        headers=_auth_headers(token),
        json={"current_password": "wrong password", "new_password": "new strong password"},
    )
    assert wrong_current.status_code == 401
    assert wrong_current.json()["code"] == 40101

    changed = client.put(
        "/api/v1/auth/password",
        headers=_auth_headers(token),
        json={
            "current_password": "correct horse battery staple",
            "new_password": "new strong password",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["data"] == {}

    assert client.get("/api/v1/auth/me", headers=_auth_headers(token)).json()["code"] == 40102
    old_login = client.post(
        "/api/v1/auth/login",
        headers=RUNTIME_HEADERS,
        json={"username": "admin", "password": "correct horse battery staple"},
    )
    assert old_login.json()["code"] == 40101
    assert _login(client, password="new strong password")


def test_logout_is_client_side_only_and_does_not_blacklist_the_token(client: TestClient) -> None:
    _bootstrap(client)
    token = _login(client)

    response = client.post("/api/v1/auth/logout", headers=_auth_headers(token))

    assert response.status_code == 200
    assert response.json()["data"] == {}
    assert client.get("/api/v1/auth/me", headers=_auth_headers(token)).status_code == 200
