from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.middleware import RuntimeSecretMiddleware
from app.main import create_app

EXPECTED_SECRET = "a" * 32


def _build_probe_app(*, expected_secret: str | None) -> FastAPI:
    probe_app = FastAPI()
    probe_app.add_middleware(RuntimeSecretMiddleware, expected_secret=expected_secret)

    @probe_app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @probe_app.get("/protected")
    async def protected() -> dict[str, str]:
        return {"status": "ok"}

    return probe_app


def test_missing_secret_header_is_rejected() -> None:
    with TestClient(_build_probe_app(expected_secret=EXPECTED_SECRET)) as client:
        response = client.get("/protected")

    assert response.status_code == 401
    assert response.json() == {"code": 40103, "msg": "运行期密钥缺失或无效", "data": {}}


def test_wrong_secret_header_is_rejected() -> None:
    with TestClient(_build_probe_app(expected_secret=EXPECTED_SECRET)) as client:
        response = client.get("/protected", headers={"X-Runtime-Secret": "wrong-secret"})

    assert response.status_code == 401


def test_correct_secret_header_is_accepted() -> None:
    with TestClient(_build_probe_app(expected_secret=EXPECTED_SECRET)) as client:
        response = client.get("/protected", headers={"X-Runtime-Secret": EXPECTED_SECRET})

    assert response.status_code == 200


def test_health_path_is_exempt_even_without_a_secret_header() -> None:
    with TestClient(_build_probe_app(expected_secret=EXPECTED_SECRET)) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_missing_expected_secret_rejects_every_request() -> None:
    with TestClient(_build_probe_app(expected_secret=None)) as client:
        response = client.get("/protected", headers={"X-Runtime-Secret": "anything"})

    assert response.status_code == 401


def test_cors_preflight_reaches_cors_middleware_before_runtime_secret_check() -> None:
    application = create_app(Settings(environment="test", runtime_secret=EXPECTED_SECRET))

    with TestClient(application) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
