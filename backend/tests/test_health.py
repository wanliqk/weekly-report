from importlib.metadata import version as package_version

from fastapi.testclient import TestClient

from app.main import create_app

_EXPECTED_VERSION = package_version("weekly-report-backend")


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app()

    assert app.title == "Weekly Report Backend"


def test_health_returns_frozen_success_body() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"

    body = response.json()
    assert set(body.keys()) == {"code", "msg", "data"}
    assert body["code"] == 0
    assert body["msg"] == "success"
    assert set(body["data"].keys()) == {"status", "version"}
    assert body["data"]["status"] == "ok"
    assert body["data"]["version"] == _EXPECTED_VERSION


def test_health_response_has_no_sensitive_fields() -> None:
    client = TestClient(create_app())

    body = client.get("/health").json()

    serialized = str(body).lower()
    forbidden_markers = ("path", "host", "user", "secret", "env", "log", "db", "database")
    for marker in forbidden_markers:
        assert marker not in serialized
