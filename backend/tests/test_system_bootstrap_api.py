from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.paths import ensure_runtime_directories
from app.db.migrate import run_startup_migrations
from app.main import create_app

RUNTIME_SECRET = "a" * 32
HEADERS = {"X-Runtime-Secret": RUNTIME_SECRET}
PASSWORD = "correct horse battery staple"


@pytest.fixture
def migrated_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backups",
        runtime_secret=RUNTIME_SECRET,
    )
    ensure_runtime_directories(settings)
    run_startup_migrations(settings)
    return settings


@pytest.fixture
def client(migrated_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(migrated_settings)) as test_client:
        yield test_client


def _payload(**overrides: str) -> dict[str, str]:
    payload = {"username": "alice", "password": PASSWORD, "display_name": "Alice"}
    payload.update(overrides)
    return payload


def test_bootstrap_status_reports_not_initialized_on_an_empty_database(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/system/bootstrap-status", headers=HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "msg": "success",
        "data": {"initialized": False},
    }


def test_bootstrap_status_requires_the_runtime_secret(client: TestClient) -> None:
    response = client.get("/api/v1/system/bootstrap-status")

    assert response.status_code == 401
    assert response.json()["code"] == 40103


def test_bootstrap_creates_the_first_user_and_fixed_admin(client: TestClient) -> None:
    response = client.post("/api/v1/system/bootstrap", headers=HEADERS, json=_payload())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "alice"
    assert data["display_name"] == "Alice"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    user_login = client.post(
        "/api/v1/auth/login",
        headers=HEADERS,
        json={"username": "alice", "password": PASSWORD},
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        headers=HEADERS,
        json={"username": "admin", "password": PASSWORD},
    )
    assert user_login.status_code == 200
    assert admin_login.status_code == 200
    assert client.get("/api/v1/system/bootstrap-status", headers=HEADERS).json()["data"] == {
        "initialized": True
    }


def test_removed_bootstrap_admin_route_is_not_available(client: TestClient) -> None:
    response = client.post("/api/v1/system/bootstrap-admin", headers=HEADERS, json=_payload())
    assert response.status_code == 404


def test_bootstrap_twice_rejects_the_second_call(client: TestClient) -> None:
    first = client.post("/api/v1/system/bootstrap", headers=HEADERS, json=_payload())
    assert first.status_code == 200

    second = client.post(
        "/api/v1/system/bootstrap",
        headers=HEADERS,
        json=_payload(username="someone-else"),
    )

    assert second.status_code == 400
    assert second.json()["code"] == 40001


@pytest.mark.parametrize(
    "payload",
    [
        _payload(password="short"),
        _payload(display_name=""),
        _payload(username="  ab  "),
        _payload(username=" ADMIN "),
    ],
)
def test_bootstrap_rejects_invalid_or_reserved_input(
    client: TestClient, payload: dict[str, str]
) -> None:
    response = client.post("/api/v1/system/bootstrap", headers=HEADERS, json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == 40001
    assert client.get("/api/v1/system/bootstrap-status", headers=HEADERS).json()["data"] == {
        "initialized": False
    }
