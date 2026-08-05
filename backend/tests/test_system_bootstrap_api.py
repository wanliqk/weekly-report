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


def test_bootstrap_admin_creates_the_first_admin_and_flips_bootstrap_status(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/system/bootstrap-admin",
        headers=HEADERS,
        json={
            "username": "admin",
            "password": "correct horse battery staple",
            "display_name": "Admin",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["username"] == "admin"
    assert data["display_name"] == "Admin"
    assert data["role"] == "admin"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    status_response = client.get("/api/v1/system/bootstrap-status", headers=HEADERS)
    assert status_response.json()["data"]["initialized"] is True


def test_bootstrap_admin_twice_rejects_the_second_call(client: TestClient) -> None:
    payload = {
        "username": "admin",
        "password": "correct horse battery staple",
        "display_name": "Admin",
    }
    first = client.post("/api/v1/system/bootstrap-admin", headers=HEADERS, json=payload)
    assert first.status_code == 200

    second = client.post(
        "/api/v1/system/bootstrap-admin",
        headers=HEADERS,
        json={**payload, "username": "someone-else"},
    )

    assert second.status_code == 400
    assert second.json()["code"] == 40001


def test_bootstrap_admin_rejects_a_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/system/bootstrap-admin",
        headers=HEADERS,
        json={"username": "admin", "password": "short", "display_name": "Admin"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001

    status_response = client.get("/api/v1/system/bootstrap-status", headers=HEADERS)
    assert status_response.json()["data"]["initialized"] is False


def test_bootstrap_admin_rejects_a_blank_display_name(client: TestClient) -> None:
    response = client.post(
        "/api/v1/system/bootstrap-admin",
        headers=HEADERS,
        json={"username": "admin", "password": "correct horse battery staple", "display_name": ""},
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_bootstrap_admin_validates_username_length_after_trimming(client: TestClient) -> None:
    response = client.post(
        "/api/v1/system/bootstrap-admin",
        headers=HEADERS,
        json={
            "username": "  ab  ",
            "password": "correct horse battery staple",
            "display_name": "Admin",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == 40001
