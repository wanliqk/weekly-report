from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_uses_the_common_response_shape() -> None:
    application = create_app(Settings(environment="test"))

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "msg": "success",
        "data": {"status": "ok", "version": application.version},
    }
    assert response.headers["Cache-Control"] == "no-store"
    assert len(response.headers["X-Request-Id"]) == 32


def test_health_is_exempt_from_runtime_secret() -> None:
    application = create_app(Settings(environment="test"))

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_health_preserves_a_safe_caller_request_id() -> None:
    application = create_app(Settings(environment="test"))

    with TestClient(application) as client:
        response = client.get("/health", headers={"X-Request-Id": "desktop-123"})

    assert response.headers["X-Request-Id"] == "desktop-123"


def test_health_replaces_an_unsafe_caller_request_id() -> None:
    application = create_app(Settings(environment="test"))

    with TestClient(application) as client:
        response = client.get("/health", headers={"X-Request-Id": "invalid request id"})

    assert response.headers["X-Request-Id"] != "invalid request id"
    assert len(response.headers["X-Request-Id"]) == 32
