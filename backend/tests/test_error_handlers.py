from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from app.core.errors import AppError, register_exception_handlers


class _Payload(BaseModel):
    name: str
    count: int


def _build_probe_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/validate")
    async def _validate(payload: _Payload) -> dict[str, str]:
        return {"name": payload.name}

    @app.get("/business-error")
    async def _business_error() -> None:
        raise AppError(
            code=40901,
            http_status=409,
            message="该工作日期已存在日报",
            data={"existing_report_id": "01K000000000000000000000"},
        )

    @app.get("/db-unavailable")
    async def _db_unavailable() -> None:
        raise OperationalError("SELECT 1", {}, Exception("database is locked"))

    @app.get("/boom")
    async def _boom() -> None:
        raise RuntimeError("unexpected failure, secret token=abc123")

    return app


def test_validation_errors_are_normalized_with_safe_field_locations() -> None:
    with TestClient(_build_probe_app()) as client:
        response = client.post("/validate", json={"name": "x"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40001
    assert body["data"]["errors"]
    assert body["data"]["errors"][0]["field"] == "count"


def test_app_error_is_converted_to_its_own_code_status_and_data() -> None:
    with TestClient(_build_probe_app()) as client:
        response = client.get("/business-error")

    assert response.status_code == 409
    assert response.json() == {
        "code": 40901,
        "msg": "该工作日期已存在日报",
        "data": {"existing_report_id": "01K000000000000000000000"},
    }


def test_operational_error_maps_to_database_unavailable_without_leaking_driver_text() -> None:
    with TestClient(_build_probe_app(), raise_server_exceptions=False) as client:
        response = client.get("/db-unavailable")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == 50301
    assert body["msg"] == "数据库繁忙或服务暂不可用"
    assert body["data"] == {}


def test_unexpected_exceptions_are_converted_without_leaking_details() -> None:
    with TestClient(_build_probe_app(), raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body == {"code": 50001, "msg": "内部错误", "data": {}}
    assert "secret" not in response.text
    assert "abc123" not in response.text
