import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

VALIDATION_ERROR_CODE = 40001
DATABASE_UNAVAILABLE_CODE = 50301
INTERNAL_ERROR_CODE = 50001

_BODY_LOCATION_PREFIX = "body"


class AppError(Exception):
    """Base class for business exceptions Services raise.

    Router/Service code raises a typed `AppError` (or a subclass with a
    fixed `code`/`http_status` for a specific business scenario); the
    handler registered here converts it into the unified response shape
    without each call site needing to know about JSONResponse.
    """

    def __init__(
        self,
        *,
        code: int,
        http_status: int,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.data = data if data is not None else {}


def _error_response(
    *, code: int, http_status: int, message: str, data: dict[str, Any]
) -> JSONResponse:
    content = {"code": code, "msg": message, "data": data}
    return JSONResponse(status_code=http_status, content=content)


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _field_path(loc: tuple[int | str, ...]) -> str:
    parts = [str(part) for part in loc if part != _BODY_LOCATION_PREFIX]
    return ".".join(parts)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            code=exc.code, http_status=exc.http_status, message=exc.message, data=exc.data
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"field": _field_path(error["loc"]), "message": error["msg"]} for error in exc.errors()
        ]
        return _error_response(
            code=VALIDATION_ERROR_CODE,
            http_status=status.HTTP_400_BAD_REQUEST,
            message="参数或业务规则校验失败",
            data={"errors": errors},
        )

    @app.exception_handler(OperationalError)
    async def _handle_database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
        logger.warning(
            "database operational error: %s",
            exc,
            extra={"request_id": _request_id(request)},
        )
        return _error_response(
            code=DATABASE_UNAVAILABLE_CODE,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="数据库繁忙或服务暂不可用",
            data={},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled exception",
            exc_info=exc,
            extra={"request_id": _request_id(request)},
        )
        return _error_response(
            code=INTERNAL_ERROR_CODE,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="内部错误",
            data={},
        )
