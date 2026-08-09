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


def test_internal_wecom_prefix_is_exempt_even_without_a_secret_header() -> None:
    """Regression test for the WECOM-06 gap: `WeComBridgeClient` never sends
    `X-Runtime-Secret` (`docs/方案设计.md` §3.1 says the internal endpoints are
    protected by `X-Main-Bridge-Secret` + JWT instead), so this middleware
    must not 401 those requests before they ever reach that check."""
    probe_app = FastAPI()
    probe_app.add_middleware(RuntimeSecretMiddleware, expected_secret=EXPECTED_SECRET)

    @probe_app.post("/api/v1/internal/wecom/sync-records/{record_id}/execute")
    async def execute(record_id: str) -> dict[str, str]:
        return {"record_id": record_id}

    with TestClient(probe_app) as client:
        response = client.post("/api/v1/internal/wecom/sync-records/abc123/execute")

    assert response.status_code == 200


def test_public_wecom_path_still_requires_the_runtime_secret() -> None:
    """The exemption must be scoped to `/api/v1/internal/wecom/**` only —
    the public `/api/v1/wecom/**` REST surface stays behind the normal
    runtime-secret gate like every other public endpoint."""
    probe_app = FastAPI()
    probe_app.add_middleware(RuntimeSecretMiddleware, expected_secret=EXPECTED_SECRET)

    @probe_app.get("/api/v1/wecom/connection")
    async def connection() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(probe_app) as client:
        response = client.get("/api/v1/wecom/connection")

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
